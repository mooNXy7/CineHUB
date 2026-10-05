package com.cinehub.tv;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import android.content.ActivityNotFoundException;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
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

public class MainActivity extends AppCompatActivity {
    private static final String LOCAL_URL = "file:///android_asset/cinehub/index.html?tv=1";
    private static final String UPDATE_URL = "https://raw.githubusercontent.com/mooNXy7/CineHUB/main/CineHUB_TV_Android/CineHUB-TV/src/main/assets/cinehub/update.json";
    private static final String UPDATE_FALLBACK_URL = "https://raw.githubusercontent.com/mooNXy7/CineHUB/main/CineHUB_TV_Android/CineHUB-TV/src/main/assets/cinehub/update.json";
    private static final int CURRENT_VERSION_CODE = 102;
    private final ExecutorService updateExecutor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private long pendingDownloadId = -1;
    private final BroadcastReceiver downloadReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
            if (id != pendingDownloadId) return;
            DownloadManager dm = (DownloadManager)getSystemService(DOWNLOAD_SERVICE);
            Uri uri = dm.getUriForDownloadedFile(id);
            if (uri != null) installApk(uri);
        }
    };
    private WebView webView;
    private View fullscreenView;
    private WebChromeClient.CustomViewCallback fullscreenCallback;

    @Override protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);
        configureWebView();
        webView.loadUrl(resolveStartUrl());
        registerDownloadReceiver();
        checkForUpdate();
    }

    private void registerDownloadReceiver() {
        IntentFilter filter = new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE);
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            registerReceiver(downloadReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(downloadReceiver, filter);
        }
    }

    private String resolveStartUrl() {
        String remote = BuildConfig.CINEHUB_REMOTE_URL;
        if (remote != null && !remote.trim().isEmpty()) return remote + (remote.contains("?") ? "&" : "?") + "tv=1";
        return LOCAL_URL;
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false); s.setAllowFileAccess(true); s.setAllowContentAccess(true);
        s.setSupportZoom(false); s.setBuiltInZoomControls(false); s.setDisplayZoomControls(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString() + " CineHUB-TV/1.0.2");
        if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) WebSettingsCompat.setForceDark(s, WebSettingsCompat.FORCE_DARK_OFF);
        webView.setBackgroundColor(Color.BLACK); webView.setFocusable(true); webView.requestFocus();
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri=request.getUrl(); String scheme=uri.getScheme();
                if ("http".equalsIgnoreCase(scheme)||"https".equalsIgnoreCase(scheme)) {
                    String host=uri.getHost(); String current=Uri.parse(resolveStartUrl()).getHost();
                    if(current==null||current.equalsIgnoreCase(host)) return false;
                    try { startActivity(new Intent(Intent.ACTION_VIEW,uri)); } catch(ActivityNotFoundException ignored){}
                    return true;
                }
                return false;
            }
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
                // Some Android TV/TV Box WebView builds can kill the renderer under memory/GPU pressure.
                // Keep the native activity alive and recreate the page instead of closing CineHUB.
                try {
                    view.post(() -> {
                        try { view.loadUrl(resolveStartUrl()); } catch (Exception ignored) { }
                    });
                } catch (Exception ignored) { }
                return true;
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onShowCustomView(View view, CustomViewCallback callback){ enterFullscreen(view,callback); }
            @Override public void onHideCustomView(){ exitFullscreen(); }
        });
        webView.setDownloadListener((url,userAgent,contentDisposition,mimeType,contentLength)->enqueueDownload(url,userAgent,mimeType));
        webView.setOnLongClickListener(v->true);
    }

    private void checkForUpdate(){
        updateExecutor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection)new URL(UPDATE_URL).openConnection();
                connection.setConnectTimeout(5000); connection.setReadTimeout(5000);
                connection.setRequestProperty("User-Agent","CineHUB-TV/"+CURRENT_VERSION_CODE);
                try (InputStream in = connection.getInputStream()) {
                    byte[] data = in.readAllBytes();
                    JSONObject json = new JSONObject(new String(data, java.nio.charset.StandardCharsets.UTF_8));
                    int remoteCode = json.optInt("versionCode", CURRENT_VERSION_CODE); String apkUrl = json.optString("apkUrl", "");
                    if (remoteCode > CURRENT_VERSION_CODE && !apkUrl.isEmpty()) mainHandler.post(() -> enqueueUpdate(apkUrl, json.optString("version", "nova versão")));
                }
            } catch (Exception ignored) { } finally { if (connection != null) connection.disconnect(); }
        });
    }

    private void enqueueUpdate(String url, String version){
        try {
            DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
            r.setTitle("CineHUB TV "+version); r.setDescription("Baixando atualização"); r.setMimeType("application/vnd.android.package-archive");
            r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            r.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, "CineHUB-TV-update.apk");
            pendingDownloadId = ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(r);
            Toast.makeText(this, "Nova versão encontrada. Download iniciado.", Toast.LENGTH_LONG).show();
        } catch (Exception ignored) { }
    }

    private void installApk(Uri uri){
        try { Intent intent = new Intent(Intent.ACTION_VIEW); intent.setDataAndType(uri, "application/vnd.android.package-archive"); intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK); startActivity(intent); }
        catch (Exception e) { Toast.makeText(this, "Atualização baixada. Abra o APK em Downloads para instalar.", Toast.LENGTH_LONG).show(); }
    }

    @Override protected void onDestroy(){
        try { unregisterReceiver(downloadReceiver); } catch (Exception ignored) { }
        updateExecutor.shutdownNow();
        super.onDestroy();
    }

    private void enqueueDownload(String url,String userAgent,String mimeType){
        try{
            DownloadManager.Request r=new DownloadManager.Request(Uri.parse(url)); r.setTitle("CineHUB TV"); r.setDescription("Download iniciado");
            if(mimeType!=null) r.setMimeType(mimeType); if(userAgent!=null) r.addRequestHeader("User-Agent",userAgent);
            r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,"CineHUB-"+System.currentTimeMillis());
            ((DownloadManager)getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(r); Toast.makeText(this,"Download iniciado",Toast.LENGTH_SHORT).show();
        }catch(Exception e){ Toast.makeText(this,"Não foi possível iniciar o download",Toast.LENGTH_SHORT).show(); }
    }

    private void enterFullscreen(View view,WebChromeClient.CustomViewCallback callback){
        if(fullscreenView!=null){callback.onCustomViewHidden();return;}
        fullscreenView=view; fullscreenCallback=callback; webView.setVisibility(View.GONE);
        ((android.view.ViewGroup)findViewById(R.id.root)).addView(view,new android.view.ViewGroup.LayoutParams(-1,-1)); hideSystemUi();
    }

    private void exitFullscreen(){
        if(fullscreenView==null)return;
        ((android.view.ViewGroup)findViewById(R.id.root)).removeView(fullscreenView); fullscreenView=null;
        if(fullscreenCallback!=null){fullscreenCallback.onCustomViewHidden();fullscreenCallback=null;}
        webView.setVisibility(View.VISIBLE); webView.requestFocus(); showSystemUi();
    }

    private void hideSystemUi(){getWindow().getDecorView().setSystemUiVisibility(5894);}
    private void showSystemUi(){getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE);}

    @Override public boolean dispatchKeyEvent(KeyEvent e){
        if(e.getAction()==KeyEvent.ACTION_DOWN){
            if(e.getKeyCode()==KeyEvent.KEYCODE_BACK){handleBack();return true;}
            if(e.getKeyCode()==KeyEvent.KEYCODE_HOME&&webView!=null){
                webView.evaluateJavascript("window.CineHUBTV&&window.CineHUBTV.goHome&&window.CineHUBTV.goHome();",null);return true;
            }
        }
        return super.dispatchKeyEvent(e);
    }

    @Override public void onBackPressed(){handleBack();}

    private void handleBack(){
        if(fullscreenView!=null){exitFullscreen();return;}
        if(webView==null){super.onBackPressed();return;}
        webView.evaluateJavascript("(function(){try{return !!(window.CineHUBTV&&window.CineHUBTV.back&&window.CineHUBTV.back());}catch(e){return false;}})();",value->{if("false".equals(value))MainActivity.super.onBackPressed();});
    }
}
