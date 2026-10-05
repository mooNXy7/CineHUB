package com.cinehub.mobile;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
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
    private static final String UPDATE_URL = "https://raw.githubusercontent.com/mooNXy7/CineHUB/main/CineHUB_Mobile_Android/update.json";
    private static final int CURRENT_VERSION_CODE = 100;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private long pendingDownloadId = -1L;
    private WebView webView;
    private View fullscreenView;
    private WebChromeClient.CustomViewCallback fullscreenCallback;

    private final BroadcastReceiver downloadReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L);
            if (id != pendingDownloadId) return;
            DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            Uri uri = dm.getUriForDownloadedFile(id);
            if (uri != null) installApk(uri);
        }
    };

    @Override protected void onCreate(@Nullable Bundle savedInstanceState) {
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
        s.setUserAgentString(s.getUserAgentString() + " CineHUB-Mobile/1.0.0");
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
                    if (host == null || host.equalsIgnoreCase("cinehub-web.pages.dev")) {
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
            @Override public void onHideCustomView() { exitFullscreen(); }
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
                connection.setRequestProperty("User-Agent", "CineHUB-Mobile/" + CURRENT_VERSION_CODE);
                try (InputStream in = connection.getInputStream()) {
                    byte[] data = in.readAllBytes();
                    JSONObject json = new JSONObject(new String(data, StandardCharsets.UTF_8));
                    int remoteCode = json.optInt("versionCode", CURRENT_VERSION_CODE);
                    String apkUrl = json.optString("apkUrl", "");
                    String version = json.optString("version", "nova versão");
                    if (remoteCode > CURRENT_VERSION_CODE && !apkUrl.isEmpty()) {
                        mainHandler.post(() -> enqueueUpdate(apkUrl, version));
                    }
                }
            } catch (Exception ignored) {
                // Update checks must never prevent the app from opening.
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private void enqueueUpdate(String url, String version) {
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle("CineHUB " + version);
            request.setDescription("Baixando atualização");
            request.setMimeType("application/vnd.android.package-archive");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, "CineHUB-Mobile-update.apk");
            pendingDownloadId = ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(request);
            Toast.makeText(this, "Nova versão encontrada. Download iniciado.", Toast.LENGTH_LONG).show();
        } catch (Exception ignored) {
            Toast.makeText(this, "Não foi possível baixar a atualização.", Toast.LENGTH_LONG).show();
        }
    }

    private void installApk(Uri uri) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception ignored) {
            Toast.makeText(this, "Atualização baixada. Abra o APK em Downloads para instalar.", Toast.LENGTH_LONG).show();
        }
    }

    private void enqueueDownload(String url, String userAgent, String mimeType) {
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle("CineHUB");
            request.setDescription("Download iniciado");
            if (mimeType != null && !mimeType.isEmpty()) request.setMimeType(mimeType);
            if (userAgent != null && !userAgent.isEmpty()) request.addRequestHeader("User-Agent", userAgent);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "CineHUB-" + System.currentTimeMillis());
            ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(request);
            Toast.makeText(this, "Download iniciado", Toast.LENGTH_SHORT).show();
        } catch (Exception ignored) {
            Toast.makeText(this, "Não foi possível iniciar o download", Toast.LENGTH_SHORT).show();
        }
    }

    private void enterFullscreen(View view, WebChromeClient.CustomViewCallback callback) {
        if (fullscreenView != null) { callback.onCustomViewHidden(); return; }
        fullscreenView = view;
        fullscreenCallback = callback;
        webView.setVisibility(View.GONE);
        ((android.view.ViewGroup) findViewById(R.id.root)).addView(view,
                new android.view.ViewGroup.LayoutParams(-1, -1));
        hideSystemUi();
    }

    private void exitFullscreen() {
        if (fullscreenView == null) return;
        ((android.view.ViewGroup) findViewById(R.id.root)).removeView(fullscreenView);
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
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    @Override public void onBackPressed() {
        if (fullscreenView != null) { exitFullscreen(); return; }
        if (webView != null && webView.canGoBack()) { webView.goBack(); return; }
        super.onBackPressed();
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        return super.dispatchKeyEvent(event);
    }

    @Override protected void onDestroy() {
        try { unregisterReceiver(downloadReceiver); } catch (Exception ignored) { }
        executor.shutdownNow();
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
