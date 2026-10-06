package com.cinehub.mobile;

import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.view.Gravity;
import android.view.ViewGroup;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.splashscreen.SplashScreen;
import androidx.webkit.WebSettingsCompat;
import androidx.webkit.WebViewFeature;
import org.json.JSONObject;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {
    private static final String START_URL = "https://cinehub-web.pages.dev/?mobile=1";
    private static final String WEB_HOST = "cinehub-web.pages.dev";
    private static final String UPDATE_URL = "https://raw.githubusercontent.com/mooNXy7/CineHUB/main/CineHUB_Mobile_Android/update.json";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private long pendingDownloadId = -1L;
    private AlertDialog downloadDialog;
    private ProgressBar downloadProgress;
    private TextView downloadProgressText;
    private Uri pendingApkUri;
    private final Handler downloadHandler = new Handler(Looper.getMainLooper());
    private WebView webView;
    private View fullscreenView;
    private WebChromeClient.CustomViewCallback fullscreenCallback;

    private final BroadcastReceiver downloadReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L);
            if (id != pendingDownloadId) return;
            DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            Uri uri = dm.getUriForDownloadedFile(id);

            if (uri != null) {
                finishDownloadAndInstall(uri);
            } else {
                stopDownloadProgress();
            }

            if (uri == null) {
                Toast.makeText(
                        MainActivity.this,
                        "Não foi possível concluir a atualização.",
                        Toast.LENGTH_LONG
                ).show();
            }
        }
    };

    @Override protected void onCreate(@Nullable Bundle savedInstanceState) {
        SplashScreen.installSplashScreen(this);
        super.onCreate(savedInstanceState);

        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);
        configureWebView();
        registerDownloadReceiver();
        webView.loadUrl(START_URL);
        checkForUpdate();
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString()
                + " CineHUB-Mobile/" + BuildConfig.VERSION_NAME);

        if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) {
            WebSettingsCompat.setForceDark(s, WebSettingsCompat.FORCE_DARK_OFF);
        }

        webView.setBackgroundColor(Color.BLACK);
        webView.setFocusable(true);
        webView.requestFocus();

        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();

                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
                    String host = uri.getHost();

                    if (host == null || host.equalsIgnoreCase(WEB_HOST)) {
                        return false;
                    }

                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, uri));
                    } catch (ActivityNotFoundException ignored) { }

                    return true;
                }

                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onShowCustomView(View view, CustomViewCallback callback) {
                enterFullscreen(view, callback);
            }

            @Override public void onHideCustomView() {
                exitFullscreen();
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) ->
                enqueueDownload(url, userAgent, mimeType));
    }

    private void registerDownloadReceiver() {
        IntentFilter filter = new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE);

        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(downloadReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(downloadReceiver, filter);
        }
    }

    private void checkForUpdate() {
        executor.execute(() -> {
            HttpURLConnection connection = null;

            try {
                connection = (HttpURLConnection) new URL(UPDATE_URL).openConnection();
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);
                connection.setUseCaches(false);
                connection.setRequestProperty("Cache-Control", "no-cache");
                connection.setRequestProperty(
                        "User-Agent",
                        "CineHUB-Mobile/" + BuildConfig.VERSION_CODE
                );

                try (InputStream in = connection.getInputStream()) {
                    byte[] data = in.readAllBytes();
                    JSONObject json = new JSONObject(
                            new String(data, StandardCharsets.UTF_8)
                    );

                    int remoteCode = json.optInt(
                            "versionCode",
                            BuildConfig.VERSION_CODE
                    );

                    String apkUrl = json.optString("apkUrl", "");
                    String version = json.optString(
                            "version",
                            "nova versão"
                    );

                    String releaseNotes = json.optString(
                            "releaseNotes",
                            "Melhorias e correções de estabilidade."
                    );

                    if (remoteCode > BuildConfig.VERSION_CODE && !apkUrl.isEmpty()) {
                        mainHandler.post(() -> showUpdateDialog(
                                version,
                                releaseNotes,
                                apkUrl
                        ));
                    }
                }
            } catch (Exception ignored) {
                // Update checks must never prevent the app from opening.
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private GradientDrawable roundedBackground(int[] colors, float radius) {
        GradientDrawable drawable = new GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                colors
        );
        drawable.setCornerRadius(radius);
        return drawable;
    }

    private TextView dialogText(String text, float size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setGravity(Gravity.CENTER_VERTICAL);
        return view;
    }

    private void showUpdateDialog(String version, String releaseNotes, String apkUrl) {
        int white = Color.WHITE;
        int muted = Color.rgb(190, 190, 195);
        int red = Color.rgb(229, 9, 20);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(34, 30, 34, 26);
        root.setBackground(roundedBackground(
                new int[]{Color.rgb(18, 18, 21), Color.rgb(5, 6, 9)},
                34f
        ));

        TextView title = dialogText("Nova atualização disponível!", 21, white);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView versionView = dialogText("VERSÃO " + version, 13, red);
        versionView.setTypeface(Typeface.DEFAULT_BOLD);
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(-1, -2);
        vp.topMargin = 10;
        root.addView(versionView, vp);

        View divider = new View(this);
        divider.setBackgroundColor(Color.rgb(90, 12, 18));
        LinearLayout.LayoutParams dp = new LinearLayout.LayoutParams(-1, 2);
        dp.topMargin = 18;
        dp.bottomMargin = 18;
        root.addView(divider, dp);

        TextView notesTitle = dialogText("Novidades", 15, white);
        notesTitle.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(notesTitle, new LinearLayout.LayoutParams(-1, -2));

        TextView notes = dialogText(releaseNotes, 14, muted);
        notes.setGravity(Gravity.TOP);
        notes.setLineSpacing(2f, 1.08f);
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(-1, -2);
        np.topMargin = 8;
        root.addView(notes, np);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, 54);
        bp.topMargin = 26;
        root.addView(buttons, bp);

        TextView later = dialogText("Mais tarde", 14, white);
        later.setGravity(Gravity.CENTER);
        later.setTypeface(Typeface.DEFAULT_BOLD);
        later.setBackground(roundedBackground(
                new int[]{Color.rgb(28, 28, 32), Color.rgb(12, 12, 15)},
                22f
        ));

        TextView install = dialogText("Instalar", 14, Color.WHITE);
        install.setGravity(Gravity.CENTER);
        install.setTypeface(Typeface.DEFAULT_BOLD);
        install.setBackground(roundedBackground(
                new int[]{Color.rgb(255, 52, 64), Color.rgb(185, 0, 12), Color.rgb(110, 0, 7)},
                22f
        ));

        LinearLayout.LayoutParams buttonParam = new LinearLayout.LayoutParams(0, -1, 1f);
        buttons.addView(later, buttonParam);
        LinearLayout.LayoutParams installParam = new LinearLayout.LayoutParams(0, -1, 1f);
        installParam.leftMargin = 12;
        buttons.addView(install, installParam);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setView(root)
                .setCancelable(true)
                .create();

        later.setOnClickListener(v -> dialog.dismiss());
        install.setOnClickListener(v -> {
            dialog.dismiss();
            enqueueUpdate(apkUrl, version);
        });

        dialog.setOnShowListener(d -> {
            if (dialog.getWindow() != null) {
                dialog.getWindow().setBackgroundDrawable(
                        roundedBackground(
                                new int[]{Color.rgb(5, 6, 9), Color.rgb(5, 6, 9)},
                                34f
                        )
                );
                dialog.getWindow().setDimAmount(0.72f);
            }
        });

        dialog.show();

        if (dialog.getWindow() != null) {
            int width = (int) (getResources().getDisplayMetrics().widthPixels * 0.90f);
            dialog.getWindow().setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT);
            dialog.getWindow().setBackgroundDrawable(
                    roundedBackground(
                            new int[]{Color.rgb(5, 6, 9), Color.rgb(5, 6, 9)},
                            34f
                    )
            );
        }
    }

    private void enqueueUpdate(String url, String version) {
        try {
            DownloadManager.Request request =
                    new DownloadManager.Request(Uri.parse(url));

            request.setTitle("CineHUB " + version);
            request.setDescription("Baixando atualização do CineHUB");
            request.setMimeType("application/vnd.android.package-archive");
            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE
            );
            request.setDestinationInExternalFilesDir(
                    this,
                    Environment.DIRECTORY_DOWNLOADS,
                    "CineHUB-Mobile-update.apk"
            );

            pendingDownloadId =
                    ((DownloadManager) getSystemService(DOWNLOAD_SERVICE))
                            .enqueue(request);

            showDownloadProgress();
            monitorDownloadProgress();

        } catch (Exception ignored) {
            Toast.makeText(
                    this,
                    "Não foi possível iniciar a atualização.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }

    private void showDownloadProgress() {
        int white = Color.WHITE;
        int muted = Color.rgb(190, 190, 195);
        int red = Color.rgb(229, 9, 20);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(34, 28, 34, 28);
        layout.setBackground(roundedBackground(
                new int[]{Color.rgb(18, 18, 21), Color.rgb(5, 6, 9)},
                30f
        ));

        TextView title = dialogText("Atualizando CineHUB", 20, white);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        layout.addView(title, new LinearLayout.LayoutParams(-1, -2));

        downloadProgressText = dialogText("Preparando atualização...", 14, muted);
        LinearLayout.LayoutParams textParams = new LinearLayout.LayoutParams(-1, -2);
        textParams.topMargin = 8;
        layout.addView(downloadProgressText, textParams);

        downloadProgress = new ProgressBar(
                this,
                null,
                android.R.attr.progressBarStyleHorizontal
        );
        downloadProgress.setMax(100);
        downloadProgress.setProgress(0);
        downloadProgress.setProgressDrawable(
                getResources().getDrawable(
                        android.R.drawable.progress_horizontal,
                        getTheme()
                )
        );

        LinearLayout.LayoutParams progressParams =
                new LinearLayout.LayoutParams(-1, 18);
        progressParams.topMargin = 24;
        layout.addView(downloadProgress, progressParams);

        TextView hint = dialogText("Não feche o CineHUB durante a atualização.", 12, muted);
        LinearLayout.LayoutParams hintParams = new LinearLayout.LayoutParams(-1, -2);
        hintParams.topMargin = 14;
        layout.addView(hint, hintParams);

        downloadDialog = new AlertDialog.Builder(this)
                .setView(layout)
                .setCancelable(false)
                .create();

        downloadDialog.setOnShowListener(d -> {
            if (downloadDialog.getWindow() != null) {
                downloadDialog.getWindow().setBackgroundDrawable(
                        roundedBackground(
                                new int[]{Color.rgb(5, 6, 9), Color.rgb(5, 6, 9)},
                                30f
                        )
                );
                downloadDialog.getWindow().setDimAmount(0.75f);
                int width = (int) (getResources().getDisplayMetrics().widthPixels * 0.90f);
                downloadDialog.getWindow().setLayout(
                        width,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );
            }
        });

        downloadDialog.show();

        if (downloadDialog.getWindow() != null) {
            int width = (int) (getResources().getDisplayMetrics().widthPixels * 0.90f);
            downloadDialog.getWindow().setLayout(
                    width,
                    ViewGroup.LayoutParams.WRAP_CONTENT
            );
        }
    }

    private void monitorDownloadProgress() {
        downloadHandler.post(new Runnable() {
            @Override public void run() {
                if (pendingDownloadId == -1L || downloadDialog == null) {
                    return;
                }

                DownloadManager dm =
                        (DownloadManager) getSystemService(DOWNLOAD_SERVICE);

                DownloadManager.Query query =
                        new DownloadManager.Query().setFilterById(pendingDownloadId);

                try (android.database.Cursor cursor = dm.query(query)) {
                    if (cursor != null && cursor.moveToFirst()) {
                        int status = cursor.getInt(
                                cursor.getColumnIndexOrThrow(
                                        DownloadManager.COLUMN_STATUS
                                )
                        );

                        if (status == DownloadManager.STATUS_FAILED) {
                            stopDownloadProgress();
                            Toast.makeText(
                                    MainActivity.this,
                                    "Falha ao baixar a atualização.",
                                    Toast.LENGTH_LONG
                            ).show();
                            return;
                        }

                        long total = cursor.getLong(
                                cursor.getColumnIndexOrThrow(
                                        DownloadManager.COLUMN_TOTAL_SIZE_BYTES
                                )
                        );
                        long downloaded = cursor.getLong(
                                cursor.getColumnIndexOrThrow(
                                        DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR
                                )
                        );

                        if (total > 0) {
                            int percent = (int) ((downloaded * 100L) / total);
                            if (downloadProgress != null) {
                                downloadProgress.setProgress(percent);
                            }
                            if (downloadProgressText != null) {
                                downloadProgressText.setText(
                                        "Baixando atualização... " + percent + "%"
                                );
                            }
                        } else if (downloadProgressText != null) {
                            downloadProgressText.setText(
                                    "Baixando atualização..."
                            );
                        }
                    }
                } catch (Exception ignored) {
                    // Continue polling until DownloadManager reports completion.
                }

                downloadHandler.postDelayed(this, 350);
            }
        });
    }

    private void stopDownloadProgress() {
        pendingDownloadId = -1L;
        downloadHandler.removeCallbacksAndMessages(null);

        if (downloadDialog != null && downloadDialog.isShowing()) {
            downloadDialog.dismiss();
        }

        downloadDialog = null;
        downloadProgress = null;
        downloadProgressText = null;
    }

    private void finishDownloadAndInstall(Uri uri) {
        if (downloadProgress != null) {
            downloadProgress.setProgress(100);
        }
        if (downloadProgressText != null) {
            downloadProgressText.setText("Download concluído. Preparando instalação...");
        }

        pendingApkUri = uri;

        downloadHandler.postDelayed(() -> {
            stopDownloadProgress();
            installApk(uri);
        }, 550);
    }

    private void installApk(Uri uri) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                && !getPackageManager().canRequestPackageInstalls()) {

            pendingApkUri = uri;

            try {
                Intent settingsIntent = new Intent(
                        Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:" + getPackageName())
                );
                settingsIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(settingsIntent);

                Toast.makeText(
                        this,
                        "Permita instalações do CineHUB. Ao voltar, a instalação será retomada.",
                        Toast.LENGTH_LONG
                ).show();

            } catch (Exception ignored) {
                Toast.makeText(
                        this,
                        "Permita instalações do CineHUB nas configurações.",
                        Toast.LENGTH_LONG
                ).show();
            }

            return;
        }

        try {
            Intent intent = new Intent(Intent.ACTION_INSTALL_PACKAGE);
            intent.setData(uri);
            intent.setType("application/vnd.android.package-archive");
            intent.addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                            | Intent.FLAG_ACTIVITY_NEW_TASK
            );
            startActivity(intent);

        } catch (Exception ignored) {
            Toast.makeText(
                    this,
                    "Não foi possível abrir o instalador da atualização.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }

    private void enqueueDownload(
            String url,
            String userAgent,
            String mimeType
    ) {
        try {
            DownloadManager.Request request =
                    new DownloadManager.Request(Uri.parse(url));

            request.setTitle("CineHUB");
            request.setDescription("Download iniciado");

            if (mimeType != null && !mimeType.isEmpty()) {
                request.setMimeType(mimeType);
            }

            if (userAgent != null && !userAgent.isEmpty()) {
                request.addRequestHeader("User-Agent", userAgent);
            }

            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
            );

            request.setDestinationInExternalPublicDir(
                    Environment.DIRECTORY_DOWNLOADS,
                    "CineHUB-" + System.currentTimeMillis()
            );

            ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE))
                    .enqueue(request);

            Toast.makeText(
                    this,
                    "Download iniciado",
                    Toast.LENGTH_SHORT
            ).show();

        } catch (Exception ignored) {
            Toast.makeText(
                    this,
                    "Não foi possível iniciar o download",
                    Toast.LENGTH_SHORT
            ).show();
        }
    }

    private void enterFullscreen(
            View view,
            WebChromeClient.CustomViewCallback callback
    ) {
        if (fullscreenView != null) {
            callback.onCustomViewHidden();
            return;
        }

        fullscreenView = view;
        fullscreenCallback = callback;

        webView.setVisibility(View.GONE);

        ((android.view.ViewGroup) findViewById(R.id.root)).addView(
                view,
                new android.view.ViewGroup.LayoutParams(-1, -1)
        );

        hideSystemUi();
    }

    private void exitFullscreen() {
        if (fullscreenView == null) return;

        ((android.view.ViewGroup) findViewById(R.id.root))
                .removeView(fullscreenView);

        fullscreenView = null;

        if (fullscreenCallback != null) {
            fullscreenCallback.onCustomViewHidden();
            fullscreenCallback = null;
        }

        webView.setVisibility(View.VISIBLE);
        webView.requestFocus();
        showSystemUi();
    }

    private void hideSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(5894);
    }

    private void showSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }

    @Override public void onBackPressed() {
        if (fullscreenView != null) {
            exitFullscreen();
            return;
        }

        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }

        super.onBackPressed();
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        return super.dispatchKeyEvent(event);
    }

    @Override protected void onResume() {
        super.onResume();

        if (pendingApkUri != null
                && Build.VERSION.SDK_INT < Build.VERSION_CODES.O
                || (pendingApkUri != null && getPackageManager().canRequestPackageInstalls())) {
            Uri uri = pendingApkUri;
            pendingApkUri = null;
            installApk(uri);
        }
    }

    @Override protected void onDestroy() {
        try {
            unregisterReceiver(downloadReceiver);
        } catch (Exception ignored) { }

        downloadHandler.removeCallbacksAndMessages(null);
        executor.shutdownNow();

        if (webView != null) {
            webView.destroy();
        }

        super.onDestroy();
    }
}
