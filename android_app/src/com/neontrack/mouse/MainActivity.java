package com.neontrack.mouse;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import java.util.List;
import android.content.res.Configuration;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.ParcelFileDescriptor;
import android.os.PowerManager;
import android.net.wifi.WifiManager;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.util.Enumeration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

public class MainActivity extends Activity {

    private WebView webView;
    private static final int CAMERA_PERMISSION_REQUEST = 101;
    private static final int FILE_CHOOSER_REQUEST = 102;
    private static final int STORAGE_PERMISSION_REQUEST = 103;
    private static final int NOTIF_PERMISSION_REQUEST = 104;
    private ValueCallback<Uri[]> mUploadMessage;
    private PermissionRequest mPendingCameraPermissionRequest;

    private static final String NOTIF_CHANNEL_ID = "pcdeck_transfers_channel";
    private static final int TRANSFER_NOTIF_ID = 2026;
    private NotificationManager notificationManager = null;

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                NOTIF_CHANNEL_ID,
                "PCDeck Transfers",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Shows live progress for active PCDeck file transfers");
            channel.setShowBadge(false);
            channel.enableVibration(false);
            channel.setSound(null, null);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private void updateTransferNotification(String title, String text, int progress, boolean ongoing) {
        try {
            if (notificationManager == null) {
                notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            }
            if (notificationManager == null) return;

            Intent intent = new Intent(this, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, intent,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0
            );

            android.app.Notification.Builder builder;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                builder = new android.app.Notification.Builder(this, NOTIF_CHANNEL_ID);
            } else {
                builder = new android.app.Notification.Builder(this);
            }

            builder.setContentTitle(title)
                   .setContentText(text)
                   .setSmallIcon(R.mipmap.ic_launcher)
                   .setContentIntent(pendingIntent)
                   .setOngoing(ongoing)
                   .setAutoCancel(!ongoing);

            if (progress >= 0 && progress <= 100 && ongoing) {
                builder.setProgress(100, progress, false);
            } else {
                builder.setProgress(0, 0, false);
            }

            notificationManager.notify(TRANSFER_NOTIF_ID, builder.build());
        } catch (Exception ignored) {}
    }

    private void clearTransferNotification() {
        try {
            if (notificationManager != null) {
                notificationManager.cancel(TRANSFER_NOTIF_ID);
            }
        } catch (Exception ignored) {}
    }

    private String formatSize(long bytes) {
        if (bytes <= 0) return "0 B";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return String.format(java.util.Locale.US, "%.1f KB", bytes / 1024.0);
        if (bytes < 1073741824L) return String.format(java.util.Locale.US, "%.1f MB", bytes / 1048576.0);
        return String.format(java.util.Locale.US, "%.2f GB", bytes / 1073741824.0);
    }

    private PowerManager.WakeLock transferWakeLock = null;
    private WifiManager.WifiLock transferWifiLock = null;
    private WifiManager.MulticastLock multicastLock = null;
    private static final int DISCOVERY_PORT = 8001;
    private long lastDiscoveryTime = 0;

    public synchronized void startUdpDiscovery() {
        long now = System.currentTimeMillis();
        if (now - lastDiscoveryTime < 800) return; // Debounce rapid triggers
        lastDiscoveryTime = now;

        new Thread(new Runnable() {
            @Override
            public void run() {
                DatagramSocket socket = null;
                try {
                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    if (wm != null) {
                        try {
                            if (multicastLock == null) {
                                multicastLock = wm.createMulticastLock("PCDeck:DiscoveryLock");
                                multicastLock.setReferenceCounted(false);
                            }
                            if (multicastLock != null && !multicastLock.isHeld()) {
                                multicastLock.acquire();
                            }
                        } catch (Exception ignored) {}
                    }

                    socket = new DatagramSocket();
                    socket.setBroadcast(true);
                    socket.setSoTimeout(1200);

                    byte[] sendData = "PCDECK_DISCOVER".getBytes("UTF-8");

                    // Collect all broadcast targets (global + active interface subnets)
                    List<InetAddress> broadcastTargets = new ArrayList<InetAddress>();
                    broadcastTargets.add(InetAddress.getByName("255.255.255.255"));

                    try {
                        Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
                        while (interfaces != null && interfaces.hasMoreElements()) {
                            NetworkInterface networkInterface = interfaces.nextElement();
                            if (networkInterface.isLoopback() || !networkInterface.isUp()) continue;
                            for (InterfaceAddress interfaceAddress : networkInterface.getInterfaceAddresses()) {
                                InetAddress broadcast = interfaceAddress.getBroadcast();
                                if (broadcast != null && !broadcastTargets.contains(broadcast)) {
                                    broadcastTargets.add(broadcast);
                                }
                            }
                        }
                    } catch (Exception ignored) {}

                    // Broadcast discovery packet to all targets
                    for (InetAddress target : broadcastTargets) {
                        try {
                            DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, target, DISCOVERY_PORT);
                            socket.send(sendPacket);
                        } catch (Exception ignored) {}
                    }

                    // Listen for instant response (< 5ms)
                    byte[] recvBuf = new byte[1024];
                    DatagramPacket recvPacket = new DatagramPacket(recvBuf, recvBuf.length);

                    long listenDeadline = System.currentTimeMillis() + 1200;
                    while (System.currentTimeMillis() < listenDeadline) {
                        try {
                            socket.receive(recvPacket);
                            String message = new String(recvPacket.getData(), 0, recvPacket.getLength(), "UTF-8").trim();
                            if (message.startsWith("PCDECK_SERVER:") || message.startsWith("PCDECK_BEACON:")) {
                                String[] parts = message.split(":");
                                final String serverPort = parts.length > 1 && !parts[1].isEmpty() ? parts[1] : "8000";
                                final String serverIp = parts.length > 3 && !parts[3].isEmpty() ? parts[3] : recvPacket.getAddress().getHostAddress();

                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        if (webView != null) {
                                            webView.evaluateJavascript("if (window.onServerDiscovered) { window.onServerDiscovered('" + serverIp + "', '" + serverPort + "'); }", null);
                                        }
                                    }
                                });
                                break; // Instant discovery complete!
                            }
                        } catch (java.net.SocketTimeoutException e) {
                            break;
                        }
                    }
                } catch (Exception ignored) {
                } finally {
                    if (socket != null) {
                        try { socket.close(); } catch (Exception ignored) {}
                    }
                    if (multicastLock != null && multicastLock.isHeld()) {
                        try { multicastLock.release(); } catch (Exception ignored) {}
                    }
                }
            }
        }, "PCDeck-UDP-Discover").start();
    }

    private synchronized void acquireTransferLocks() {
        try {
            if (transferWakeLock == null) {
                PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                if (pm != null) {
                    transferWakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PCDeck:TransferWakeLock");
                    transferWakeLock.setReferenceCounted(false);
                }
            }
            if (transferWakeLock != null && !transferWakeLock.isHeld()) {
                transferWakeLock.acquire(3600000); // 1 hour max safety limit
            }
        } catch (Exception ignored) {}

        try {
            if (transferWifiLock == null) {
                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm != null) {
                    transferWifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "PCDeck:TransferWifiLock");
                    transferWifiLock.setReferenceCounted(false);
                }
            }
            if (transferWifiLock != null && !transferWifiLock.isHeld()) {
                transferWifiLock.acquire();
            }
        } catch (Exception ignored) {}
    }

    private synchronized void releaseTransferLocks() {
        try {
            if (transferWakeLock != null && transferWakeLock.isHeld()) {
                transferWakeLock.release();
            }
        } catch (Exception ignored) {}
        try {
            if (transferWifiLock != null && transferWifiLock.isHeld()) {
                transferWifiLock.release();
            }
        } catch (Exception ignored) {}
    }

    public boolean hasStorageAccessPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return Environment.isExternalStorageManager();
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
        }
        return true;
    }

    public void requestAllStorageAccess() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                        if (!Environment.isExternalStorageManager()) {
                            try {
                                Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                                intent.setData(Uri.parse("package:" + getPackageName()));
                                startActivityForResult(intent, STORAGE_PERMISSION_REQUEST);
                            } catch (Exception e) {
                                Intent intent = new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION);
                                startActivityForResult(intent, STORAGE_PERMISSION_REQUEST);
                            }
                        } else {
                            Toast.makeText(MainActivity.this, "Full storage access already granted", Toast.LENGTH_SHORT).show();
                        }
                    } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        List<String> perms = new ArrayList<String>();
                        if (checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                            perms.add(Manifest.permission.READ_EXTERNAL_STORAGE);
                        }
                        if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                            perms.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
                        }
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            if (checkSelfPermission(Manifest.permission.READ_MEDIA_IMAGES) != PackageManager.PERMISSION_GRANTED) {
                                perms.add(Manifest.permission.READ_MEDIA_IMAGES);
                            }
                            if (checkSelfPermission(Manifest.permission.READ_MEDIA_VIDEO) != PackageManager.PERMISSION_GRANTED) {
                                perms.add(Manifest.permission.READ_MEDIA_VIDEO);
                            }
                            if (checkSelfPermission(Manifest.permission.READ_MEDIA_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                                perms.add(Manifest.permission.READ_MEDIA_AUDIO);
                            }
                        }
                        if (!perms.isEmpty()) {
                            requestPermissions(perms.toArray(new String[0]), STORAGE_PERMISSION_REQUEST);
                        } else {
                            Toast.makeText(MainActivity.this, "Full storage access already granted", Toast.LENGTH_SHORT).show();
                        }
                    }
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Cannot request storage permissions: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    public void installDownloadedApk(File apkFile) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!getPackageManager().canRequestPackageInstalls()) {
                    Toast.makeText(this, "Please allow PCDeck to install app updates", Toast.LENGTH_LONG).show();
                    Intent settingsIntent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES);
                    settingsIntent.setData(Uri.parse("package:" + getPackageName()));
                    startActivity(settingsIntent);
                }
            }

            Intent intent = new Intent(Intent.ACTION_VIEW);
            Uri apkUri = GenericFileProvider.getUriForFile(apkFile);
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "Cannot launch installer: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    public class WebAppInterface {
        Context mContext;
        private boolean isProActive = false;

        WebAppInterface(Context c) {
            mContext = c;
        }

        @JavascriptInterface
        public int getAppVersionCode() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
            } catch (Exception e) {
                return 264;
            }
        }

        @JavascriptInterface
        public String getAppVersionName() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            } catch (Exception e) {
                return "2.6.4";
            }
        }

        @JavascriptInterface
        public boolean isNativeApp() {
            return true;
        }

        @JavascriptInterface
        public void discoverServer() {
            MainActivity.this.startUdpDiscovery();
        }

        @JavascriptInterface
        public String getDeviceIp() {
            try {
                Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
                while (interfaces != null && interfaces.hasMoreElements()) {
                    NetworkInterface iface = interfaces.nextElement();
                    if (iface.isLoopback() || !iface.isUp()) continue;
                    for (InterfaceAddress addr : iface.getInterfaceAddresses()) {
                        InetAddress inet = addr.getAddress();
                        if (inet != null && !inet.isLoopbackAddress() && inet instanceof java.net.Inet4Address) {
                            return inet.getHostAddress();
                        }
                    }
                }
            } catch (Exception ignored) {}
            return "";
        }

        @JavascriptInterface
        public void vibrate(long ms) {
            try {
                android.os.Vibrator v = (android.os.Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null && v.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        v.vibrate(android.os.VibrationEffect.createOneShot(Math.max(1, Math.min(500, ms)), android.os.VibrationEffect.DEFAULT_AMPLITUDE));
                    } else {
                        v.vibrate(Math.max(1, Math.min(500, ms)));
                    }
                }
            } catch (Exception e) {}
        }

        @JavascriptInterface
        public void downloadAndInstallApk(final String apkDownloadUrl) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    HttpURLConnection connection = null;
                    InputStream input = null;
                    OutputStream output = null;
                    try {
                        URL url = new URL(apkDownloadUrl);
                        connection = (HttpURLConnection) url.openConnection();
                        connection.setRequestProperty("User-Agent", "PCDeck-Android-App/2.6.4");
                        connection.setConnectTimeout(15000);
                        connection.setReadTimeout(30000);
                        connection.connect();

                        final int responseCode = connection.getResponseCode();
                        if (responseCode != HttpURLConnection.HTTP_OK) {
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    if (webView != null) {
                                        webView.evaluateJavascript("window.onApkUpdateError && window.onApkUpdateError('Download failed (HTTP " + responseCode + ")');", null);
                                    }
                                    Toast.makeText(MainActivity.this, "Update download failed (HTTP " + responseCode + ")", Toast.LENGTH_SHORT).show();
                                }
                            });
                            return;
                        }

                        int fileLength = connection.getContentLength();
                        File updateDir = new File(getExternalFilesDir(null), "updates");
                        if (!updateDir.exists()) {
                            updateDir.mkdirs();
                        }
                        final File apkFile = new File(updateDir, "PCDeck_Update.apk");
                        if (apkFile.exists()) {
                            apkFile.delete();
                        }

                        input = connection.getInputStream();
                        output = new FileOutputStream(apkFile);

                        byte[] data = new byte[16384];
                        long total = 0;
                        int count;
                        long lastReportTime = 0;

                        while ((count = input.read(data)) != -1) {
                            total += count;
                            output.write(data, 0, count);
                            long now = System.currentTimeMillis();
                            if (fileLength > 0 && now - lastReportTime > 120) {
                                lastReportTime = now;
                                final int percent = (int) (total * 100 / fileLength);
                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        if (webView != null) {
                                            webView.evaluateJavascript("window.onApkUpdateProgress && window.onApkUpdateProgress(" + percent + ");", null);
                                        }
                                    }
                                });
                            }
                        }

                        output.flush();

                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (webView != null) {
                                    webView.evaluateJavascript("window.onApkUpdateProgress && window.onApkUpdateProgress(100);", null);
                                }
                                installDownloadedApk(apkFile);
                            }
                        });

                    } catch (final Exception e) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (webView != null) {
                                    webView.evaluateJavascript("window.onApkUpdateError && window.onApkUpdateError(" + JSONObject.quote(e.getMessage()) + ");", null);
                                }
                                Toast.makeText(MainActivity.this, "Update error: " + e.getMessage(), Toast.LENGTH_LONG).show();
                            }
                        });
                    } finally {
                        try {
                            if (output != null) output.close();
                            if (input != null) input.close();
                            if (connection != null) connection.disconnect();
                        } catch (Exception ignored) {}
                    }
                }
            }).start();
        }

        @JavascriptInterface
        public void setProStatus(final boolean isPro) {
            this.isProActive = isPro;
            try {
                getSharedPreferences("pcdeck_prefs", Context.MODE_PRIVATE).edit().putBoolean("is_pro", isPro).apply();
            } catch (Exception ignored) {}
        }

        public boolean isProUser() {
            try {
                return isProActive || getSharedPreferences("pcdeck_prefs", Context.MODE_PRIVATE).getBoolean("is_pro", false);
            } catch (Exception e) {
                return isProActive;
            }
        }

        @JavascriptInterface
        public void setOrientation(final String mode) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if ("landscape".equalsIgnoreCase(mode)) {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
                    } else if ("portrait".equalsIgnoreCase(mode)) {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
                    } else if ("sensor".equalsIgnoreCase(mode)) {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR);
                    }
                }
            });
        }

        @JavascriptInterface
        public void toggleOrientation() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    int currentOrientation = getResources().getConfiguration().orientation;
                    if (currentOrientation == Configuration.ORIENTATION_LANDSCAPE) {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
                    } else {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
                    }
                }
            });
        }

        @JavascriptInterface
        public String getOrientation() {
            int currentOrientation = getResources().getConfiguration().orientation;
            return currentOrientation == Configuration.ORIENTATION_LANDSCAPE ? "landscape" : "portrait";
        }

        @JavascriptInterface
        public void saveFileToDownloads(final String fileUrl, final String fileName) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    acquireTransferLocks();
                    HttpURLConnection conn = null;
                    java.io.InputStream input = null;
                    java.io.OutputStream output = null;
                    Uri insertedUri = null;
                    File writtenFile = null;
                    try {
                        updateTransferNotification("📥 Downloading " + fileName, "Connecting to PC...", 0, true);

                        URL url = new URL(fileUrl);
                        conn = (HttpURLConnection) url.openConnection();
                        conn.setRequestProperty("Connection", "Keep-Alive");
                        conn.setRequestProperty("Accept-Encoding", "identity");
                        conn.setRequestProperty("User-Agent", "PCDeck/2.1");
                        conn.setConnectTimeout(15000);
                        conn.setReadTimeout(30000); // 30s timeout preventing indefinite socket hangs
                        conn.connect();

                        int responseCode = conn.getResponseCode();
                        if (responseCode < 200 || responseCode >= 300) {
                            throw new Exception("HTTP " + responseCode);
                        }

                        final long fileLength = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) ? conn.getContentLengthLong() : conn.getContentLength();
                        input = new java.io.BufferedInputStream(conn.getInputStream(), 131072);

                        File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "PCDeck");
                        if (!dir.exists()) dir.mkdirs();
                        File targetFile = new File(dir, fileName);

                        try {
                            output = new java.io.BufferedOutputStream(new FileOutputStream(targetFile), 131072);
                            writtenFile = targetFile;
                        } catch (Exception eDirect) {
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                                ContentValues values = new ContentValues();
                                values.put(MediaStore.MediaColumns.DISPLAY_NAME, fileName);
                                values.put(MediaStore.MediaColumns.MIME_TYPE, getMimeType(fileName));
                                values.put(MediaStore.MediaColumns.RELATIVE_PATH, "Download/PCDeck");
                                values.put(MediaStore.MediaColumns.IS_PENDING, 1);
                                insertedUri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                                if (insertedUri == null) {
                                    throw new Exception("Cannot create download storage stream");
                                }
                                output = new java.io.BufferedOutputStream(getContentResolver().openOutputStream(insertedUri), 131072);
                            } else {
                                throw eDirect;
                            }
                        }

                        byte[] data = new byte[131072]; // 128KB Smooth High-Throughput Chunk Buffer
                        long total = 0;
                        int count;
                        long startTime = System.currentTimeMillis();
                        long lastWebUpdate = startTime;
                        long lastNotifUpdate = startTime;

                        final boolean isPro = isProUser();
                        final long maxBytesPerSec = isPro ? 0 : 10485760L; // Free: 10 MB/s, Pro: Uncapped Turbo

                        while ((count = input.read(data)) != -1) {
                            total += count;
                            if (output != null) output.write(data, 0, count);

                            if (maxBytesPerSec > 0) {
                                long expectedMs = (total * 1000L) / maxBytesPerSec;
                                long elapsedMs = System.currentTimeMillis() - startTime;
                                if (expectedMs > elapsedMs) {
                                    long sleepMs = expectedMs - elapsedMs;
                                    if (sleepMs > 0 && sleepMs <= 500) {
                                        try { Thread.sleep(sleepMs); } catch (InterruptedException ignored) {}
                                    }
                                }
                            }

                            final int progress = fileLength > 0 ? (int) (total * 100 / fileLength) : 0;
                            final long currentTotal = total;

                            long now = System.currentTimeMillis();
                            boolean isFinished = (progress == 100 || (fileLength > 0 && total == fileLength));

                            if (now - lastWebUpdate > 250 || isFinished) {
                                lastWebUpdate = now;
                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        if (webView != null) {
                                            webView.evaluateJavascript("if(window.onNativeDownloadProgress) window.onNativeDownloadProgress(" + progress + ", " + currentTotal + ", " + fileLength + ");", null);
                                        }
                                    }
                                });
                            }

                            if (now - lastNotifUpdate > 1200 || isFinished) {
                                lastNotifUpdate = now;
                                double elapsedSec = (now - startTime) / 1000.0;
                                double speedMb = elapsedSec > 0.2 ? (total / 1048576.0) / elapsedSec : 0;
                                final String speedStr = speedMb > 0 ? String.format("%.1f MB/s", speedMb) : "--";

                                updateTransferNotification(
                                    "📥 Downloading " + fileName,
                                    progress + "% (" + formatSize(currentTotal) + " of " + formatSize(fileLength) + ") • " + speedStr,
                                    progress,
                                    true
                                );
                            }
                        }

                        if (output != null) {
                            output.flush();
                            output.close();
                            output = null;
                        }

                        // Complete pending MediaStore entry or scan file
                        if (insertedUri != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            try {
                                ContentValues values = new ContentValues();
                                values.put(MediaStore.MediaColumns.IS_PENDING, 0);
                                getContentResolver().update(insertedUri, values, null, null);
                            } catch (Exception ignored) {}
                        }

                        if (writtenFile != null && writtenFile.exists()) {
                            try {
                                android.media.MediaScannerConnection.scanFile(
                                    MainActivity.this,
                                    new String[]{writtenFile.getAbsolutePath()},
                                    new String[]{getMimeType(fileName)},
                                    null
                                );
                            } catch (Exception ignored) {}
                        }

                        final boolean verified = (fileLength <= 0 || total == fileLength);
                        updateTransferNotification(
                            "✅ Download Verified & Saved",
                            "Saved " + fileName + " (" + formatSize(total) + ")",
                            100,
                            false
                        );

                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(MainActivity.this, "Saved to Downloads/PCDeck/" + fileName + " (Verified)", Toast.LENGTH_SHORT).show();
                                if (webView != null) {
                                    webView.evaluateJavascript("if(window.onNativeDownloadComplete) window.onNativeDownloadComplete('" + fileName.replace("'", "\\'") + "', " + verified + ");", null);
                                }
                            }
                        });
                    } catch (final Exception e) {
                        if (insertedUri != null) {
                            try { getContentResolver().delete(insertedUri, null, null); } catch (Exception ignored) {}
                        }
                        updateTransferNotification("❌ Download Failed", "Error on " + fileName + ": " + e.getMessage(), 0, false);
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(MainActivity.this, "Download error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                                if (webView != null) {
                                    webView.evaluateJavascript("if(window.onNativeDownloadError) window.onNativeDownloadError('" + (e.getMessage() != null ? e.getMessage().replace("'", "\\'") : "Download error") + "');", null);
                                }
                            }
                        });
                    } finally {
                        releaseTransferLocks();
                        try { if (output != null) output.close(); } catch (Exception ignored) {}
                        try { if (input != null) input.close(); } catch (Exception ignored) {}
                        try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
                    }
                }
            }).start();
        }

        private String getMimeType(String fileName) {
            String ext = "";
            int i = fileName.lastIndexOf('.');
            if (i > 0) ext = fileName.substring(i + 1).toLowerCase();
            String mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
            return (mime != null) ? mime : "application/octet-stream";
        }

        @JavascriptInterface
        public boolean hasStoragePermission() {
            return MainActivity.this.hasStorageAccessPermission();
        }

        @JavascriptInterface
        public void requestStoragePermission() {
            MainActivity.this.requestAllStorageAccess();
        }

        @JavascriptInterface
        public String getPhonePlaces() {
            try {
                JSONArray arr = new JSONArray();

                JSONObject p1 = new JSONObject();
                p1.put("name", "Received from PC");
                p1.put("path", "default");
                p1.put("icon", "📥");
                arr.put(p1);

                JSONObject p2 = new JSONObject();
                p2.put("name", "Internal Storage");
                p2.put("path", "root");
                p2.put("icon", "📱");
                arr.put(p2);

                JSONObject p3 = new JSONObject();
                p3.put("name", "Camera / DCIM");
                p3.put("path", "dcim");
                p3.put("icon", "📸");
                arr.put(p3);

                JSONObject p4 = new JSONObject();
                p4.put("name", "Pictures");
                p4.put("path", "pictures");
                p4.put("icon", "🖼️");
                arr.put(p4);

                JSONObject p5 = new JSONObject();
                p5.put("name", "Videos & Movies");
                p5.put("path", "movies");
                p5.put("icon", "🎬");
                arr.put(p5);

                JSONObject p6 = new JSONObject();
                p6.put("name", "Downloads");
                p6.put("path", "downloads");
                p6.put("icon", "⬇️");
                arr.put(p6);

                JSONObject p7 = new JSONObject();
                p7.put("name", "Documents");
                p7.put("path", "documents");
                p7.put("icon", "📄");
                arr.put(p7);

                JSONObject p8 = new JSONObject();
                p8.put("name", "Music");
                p8.put("path", "music");
                p8.put("icon", "🎵");
                arr.put(p8);

                return arr.toString();
            } catch (Exception e) {
                return "[]";
            }
        }

        @JavascriptInterface
        public void openDownloadsFolder() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Intent intent = new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS);
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(intent);
                    } catch (Exception e) {
                        try {
                            Intent intent = new Intent(Intent.ACTION_VIEW);
                            File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "PCDeck");
                            if (!dir.exists()) dir.mkdirs();
                            Uri uri = Uri.parse(dir.getAbsolutePath());
                            intent.setDataAndType(uri, "*/*");
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(intent);
                        } catch (Exception e2) {
                            Toast.makeText(MainActivity.this, "Open your File Manager -> Downloads -> PCDeck to view files", Toast.LENGTH_LONG).show();
                        }
                    }
                }
            });
        }

        @JavascriptInterface
        public String listPhoneDirectory(final String reqPath) {
            try {
                File rootStorage = Environment.getExternalStorageDirectory();
                File targetDir;
                String displayName = "";
                String categoryType = "";

                if (reqPath == null || reqPath.trim().isEmpty() || reqPath.equals("default") || reqPath.equals("transfers")) {
                    targetDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "PCDeck");
                    if (!targetDir.exists()) {
                        targetDir.mkdirs();
                    }
                    displayName = "Received from PC";
                    categoryType = "transfers";
                } else if ("root".equalsIgnoreCase(reqPath) || "storage".equalsIgnoreCase(reqPath) || "internal".equalsIgnoreCase(reqPath) || "/".equals(reqPath)) {
                    targetDir = rootStorage;
                    displayName = "Internal Storage";
                    categoryType = "root";
                } else if ("downloads".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                    displayName = "Downloads";
                    categoryType = "downloads";
                } else if ("dcim".equalsIgnoreCase(reqPath) || "camera".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM);
                    displayName = "Camera / DCIM";
                    categoryType = "dcim";
                } else if ("pictures".equalsIgnoreCase(reqPath) || "images".equalsIgnoreCase(reqPath) || "photos".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES);
                    displayName = "Pictures";
                    categoryType = "pictures";
                } else if ("movies".equalsIgnoreCase(reqPath) || "videos".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES);
                    displayName = "Videos & Movies";
                    categoryType = "movies";
                } else if ("documents".equalsIgnoreCase(reqPath) || "docs".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS);
                    displayName = "Documents";
                    categoryType = "documents";
                } else if ("music".equalsIgnoreCase(reqPath) || "audio".equalsIgnoreCase(reqPath)) {
                    targetDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC);
                    displayName = "Music";
                    categoryType = "music";
                } else if (reqPath.startsWith("/")) {
                    targetDir = new File(reqPath);
                    displayName = targetDir.getName();
                } else {
                    targetDir = new File(rootStorage, reqPath);
                    displayName = targetDir.getName();
                }

                if (!targetDir.exists()) {
                    targetDir.mkdirs();
                }

                String currentPath = targetDir.getAbsolutePath();
                String parentPath = targetDir.getParent();
                if (parentPath == null || targetDir.equals(rootStorage) || targetDir.getAbsolutePath().equals(rootStorage.getAbsolutePath())) {
                    parentPath = "";
                }

                if (displayName == null || displayName.isEmpty()) {
                    displayName = targetDir.getName();
                    if (displayName == null || displayName.isEmpty() || displayName.equals("0") || displayName.equals("emulated")) {
                        displayName = "Internal Storage";
                    }
                }

                JSONObject res = new JSONObject();
                res.put("status", "ok");
                res.put("current_path", currentPath);
                res.put("parent_path", parentPath);
                res.put("name", displayName);
                res.put("has_permission", hasStorageAccessPermission());

                JSONArray foldersArr = new JSONArray();
                JSONArray filesArr = new JSONArray();
                Set<String> addedPaths = new HashSet<String>();

                List<JSONObject> rawFolders = new ArrayList<JSONObject>();
                List<JSONObject> rawFiles = new ArrayList<JSONObject>();

                File[] items = targetDir.listFiles();
                if (items != null) {
                    for (File f : items) {
                        if (f.getName().startsWith(".")) continue;
                        if (f.isDirectory()) {
                            JSONObject fo = new JSONObject();
                            fo.put("name", f.getName());
                            fo.put("path", f.getAbsolutePath());
                            File[] sub = f.listFiles();
                            fo.put("item_count", sub != null ? sub.length : 0);
                            fo.put("modified", f.lastModified() / 1000);
                            rawFolders.add(fo);
                        } else if (f.isFile()) {
                            JSONObject fi = new JSONObject();
                            fi.put("name", f.getName());
                            fi.put("path", f.getAbsolutePath());
                            long sz = f.length();
                            fi.put("size", sz);
                            fi.put("size_formatted", formatSize(sz));
                            String ext = "";
                            int dot = f.getName().lastIndexOf('.');
                            if (dot > 0) ext = f.getName().substring(dot + 1).toLowerCase();
                            fi.put("ext", ext);
                            fi.put("modified", f.lastModified() / 1000);
                            fi.put("mime", getMimeType(f.getName()));
                            rawFiles.add(fi);
                            addedPaths.add(f.getAbsolutePath());
                        }
                    }
                }

                // Check MediaStore for items if directory or Category matches
                if (!categoryType.isEmpty() || "dcim".equalsIgnoreCase(targetDir.getName()) || "pictures".equalsIgnoreCase(targetDir.getName()) || "movies".equalsIgnoreCase(targetDir.getName()) || "download".equalsIgnoreCase(targetDir.getName()) || "downloads".equalsIgnoreCase(targetDir.getName()) || "pcdeck".equalsIgnoreCase(targetDir.getName()) || "pcdeck_pro".equalsIgnoreCase(targetDir.getName())) {
                    queryMediaStoreForDirectory(targetDir, categoryType, rawFiles, addedPaths);
                }

                // Sort Folders Alphabetically
                Collections.sort(rawFolders, new Comparator<JSONObject>() {
                    @Override
                    public int compare(JSONObject a, JSONObject b) {
                        return a.optString("name", "").compareToIgnoreCase(b.optString("name", ""));
                    }
                });

                // Sort Files by Newest Modified First
                Collections.sort(rawFiles, new Comparator<JSONObject>() {
                    @Override
                    public int compare(JSONObject a, JSONObject b) {
                        long modA = a.optLong("modified", 0);
                        long modB = b.optLong("modified", 0);
                        if (modB != modA) {
                            return Long.compare(modB, modA);
                        }
                        return a.optString("name", "").compareToIgnoreCase(b.optString("name", ""));
                    }
                });

                for (JSONObject fo : rawFolders) foldersArr.put(fo);
                for (JSONObject fi : rawFiles) filesArr.put(fi);

                res.put("folders", foldersArr);
                res.put("files", filesArr);
                res.put("total_items", foldersArr.length() + filesArr.length());
                return res.toString();
            } catch (Exception e) {
                try {
                    JSONObject err = new JSONObject();
                    err.put("status", "error");
                    err.put("error", e.getMessage());
                    return err.toString();
                } catch (Exception ignored) {
                    return "{\"status\":\"error\"}";
                }
            }
        }

        private void queryMediaStoreForDirectory(File targetDir, String categoryType, List<JSONObject> filesList, Set<String> addedPaths) {
            try {
                ContentResolver cr = getContentResolver();
                Uri contentUri;
                if ("dcim".equalsIgnoreCase(categoryType) || "pictures".equalsIgnoreCase(categoryType)) {
                    contentUri = MediaStore.Images.Media.EXTERNAL_CONTENT_URI;
                } else if ("movies".equalsIgnoreCase(categoryType)) {
                    contentUri = MediaStore.Video.Media.EXTERNAL_CONTENT_URI;
                } else if ("music".equalsIgnoreCase(categoryType)) {
                    contentUri = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI;
                } else if ("transfers".equalsIgnoreCase(categoryType) || "downloads".equalsIgnoreCase(categoryType)) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        contentUri = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
                    } else {
                        contentUri = MediaStore.Files.getContentUri("external");
                    }
                } else {
                    contentUri = MediaStore.Files.getContentUri("external");
                }

                String[] projection = new String[]{
                    MediaStore.MediaColumns._ID,
                    MediaStore.MediaColumns.DISPLAY_NAME,
                    MediaStore.MediaColumns.DATA,
                    MediaStore.MediaColumns.SIZE,
                    MediaStore.MediaColumns.DATE_MODIFIED,
                    MediaStore.MediaColumns.MIME_TYPE
                };

                Cursor cursor = cr.query(contentUri, projection, null, null, MediaStore.MediaColumns.DATE_MODIFIED + " DESC");
                if (cursor != null) {
                    int idCol = cursor.getColumnIndex(MediaStore.MediaColumns._ID);
                    int nameCol = cursor.getColumnIndex(MediaStore.MediaColumns.DISPLAY_NAME);
                    int dataCol = cursor.getColumnIndex(MediaStore.MediaColumns.DATA);
                    int sizeCol = cursor.getColumnIndex(MediaStore.MediaColumns.SIZE);
                    int dateCol = cursor.getColumnIndex(MediaStore.MediaColumns.DATE_MODIFIED);
                    int mimeCol = cursor.getColumnIndex(MediaStore.MediaColumns.MIME_TYPE);

                    int count = 0;
                    while (cursor.moveToNext() && count < 300) {
                        String path = dataCol >= 0 ? cursor.getString(dataCol) : null;
                        String name = nameCol >= 0 ? cursor.getString(nameCol) : null;
                        long size = sizeCol >= 0 ? cursor.getLong(sizeCol) : 0;
                        long mod = dateCol >= 0 ? cursor.getLong(dateCol) : 0;
                        String mime = mimeCol >= 0 ? cursor.getString(mimeCol) : "";

                        if (path == null && idCol >= 0) {
                            long id = cursor.getLong(idCol);
                            path = ContentUris.withAppendedId(contentUri, id).toString();
                        }

                        if (name == null && path != null && !path.startsWith("content://")) {
                            name = new File(path).getName();
                        }
                        if (name == null || name.isEmpty() || name.startsWith(".")) continue;
                        if (path == null) path = targetDir.getAbsolutePath() + "/" + name;

                        if (addedPaths.contains(path) || addedPaths.contains(name)) continue;
                        addedPaths.add(path);
                        addedPaths.add(name);

                        JSONObject fi = new JSONObject();
                        fi.put("name", name);
                        fi.put("path", path);
                        fi.put("size", size);
                        fi.put("size_formatted", formatSize(size));
                        String ext = "";
                        int dot = name.lastIndexOf('.');
                        if (dot > 0) ext = name.substring(dot + 1).toLowerCase();
                        fi.put("ext", ext);
                        fi.put("modified", mod);
                        fi.put("mime", mime != null && !mime.isEmpty() ? mime : getMimeType(name));
                        filesList.add(fi);
                        count++;
                    }
                    cursor.close();
                }
            } catch (Exception ignored) {}
        }

        private String formatSize(long bytes) {
            if (bytes <= 0) return "0 B";
            if (bytes < 1024) return bytes + " B";
            if (bytes < 1048576) return String.format("%.1f KB", bytes / 1024.0);
            if (bytes < 1073741824L) return String.format("%.1f MB", bytes / 1048576.0);
            return String.format("%.2f GB", bytes / 1073741824.0);
        }

        @JavascriptInterface
        public boolean deletePhoneFile(String filePath) {
            try {
                if (filePath == null || filePath.isEmpty()) return false;
                if (filePath.startsWith("content://")) {
                    Uri uri = Uri.parse(filePath);
                    return getContentResolver().delete(uri, null, null) > 0;
                }
                File f = new File(filePath);
                if (f.exists()) {
                    if (f.isDirectory()) {
                        deleteRecursive(f);
                        return true;
                    } else {
                        return f.delete();
                    }
                }
                return false;
            } catch (Exception e) {
                return false;
            }
        }

        private void deleteRecursive(File fileOrDirectory) {
            if (fileOrDirectory.isDirectory()) {
                File[] files = fileOrDirectory.listFiles();
                if (files != null) {
                    for (File child : files) {
                        deleteRecursive(child);
                    }
                }
            }
            fileOrDirectory.delete();
        }

        @JavascriptInterface
        public void openPhoneFile(final String filePath) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        if (filePath == null || filePath.isEmpty()) {
                            Toast.makeText(MainActivity.this, "Invalid file path", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        if (filePath.startsWith("content://")) {
                            Uri contentUri = Uri.parse(filePath);
                            Intent intent = new Intent(Intent.ACTION_VIEW);
                            intent.setDataAndType(contentUri, "*/*");
                            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(intent);
                            return;
                        }
                        File file = new File(filePath);
                        if (!file.exists()) {
                            Toast.makeText(MainActivity.this, "File does not exist on phone", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        Intent intent = new Intent(Intent.ACTION_VIEW);
                        String mime = getMimeType(file.getName());
                        if (mime == null || mime.isEmpty()) mime = "*/*";

                        Uri contentUri = GenericFileProvider.getUriForFile(file);
                        intent.setDataAndType(contentUri, mime);
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);

                        PackageManager pm = getPackageManager();
                        List<ResolveInfo> resInfoList = pm.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY);
                        if (resInfoList.isEmpty()) {
                            intent.setDataAndType(contentUri, "*/*");
                            resInfoList = pm.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY);
                        }

                        for (ResolveInfo resolveInfo : resInfoList) {
                            String packageName = resolveInfo.activityInfo.packageName;
                            grantUriPermission(packageName, contentUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        }

                        Intent chooser = Intent.createChooser(intent, "Open " + file.getName());
                        chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(chooser);
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Opening file: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }

        @JavascriptInterface
        public boolean createPhoneFolder(String parentPath, String folderName) {
            try {
                File parent = new File(parentPath);
                if (!parent.exists()) parent.mkdirs();
                File newDir = new File(parent, folderName);
                return newDir.mkdirs();
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public void uploadPhoneFileToPc(final String filePath, final String pcDestDir, final String serverUrl) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    acquireTransferLocks();
                    HttpURLConnection conn = null;
                    InputStream inputStream = null;
                    OutputStream outputStream = null;
                    String fileName = "";
                    try {
                        long totalBytes = 0;

                        if (filePath.startsWith("content://")) {
                            Uri uri = Uri.parse(filePath);
                            try {
                                inputStream = getContentResolver().openInputStream(uri);
                                ParcelFileDescriptor pfd = getContentResolver().openFileDescriptor(uri, "r");
                                if (pfd != null) {
                                    totalBytes = pfd.getStatSize();
                                    pfd.close();
                                }
                            } catch (Exception ignored) {}
                            Cursor cursor = null;
                            try {
                                cursor = getContentResolver().query(uri, null, null, null, null);
                                if (cursor != null && cursor.moveToFirst()) {
                                    int nameIdx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                                    int sizeIdx = cursor.getColumnIndex(OpenableColumns.SIZE);
                                    if (nameIdx >= 0) fileName = cursor.getString(nameIdx);
                                    if (sizeIdx >= 0 && totalBytes <= 0) totalBytes = cursor.getLong(sizeIdx);
                                }
                            } catch (Exception ignored) {}
                            finally {
                                if (cursor != null) cursor.close();
                            }
                        } else {
                            File file = new File(filePath);
                            if (file.exists() && file.isFile()) {
                                try {
                                    inputStream = new FileInputStream(file);
                                    totalBytes = file.length();
                                    fileName = file.getName();
                                } catch (Exception ignored) {}
                            }

                            if (inputStream == null) {
                                try {
                                    Uri fileUri = Uri.fromFile(file);
                                    inputStream = getContentResolver().openInputStream(fileUri);
                                    if (file.exists()) {
                                        if (totalBytes <= 0) totalBytes = file.length();
                                        if (fileName == null || fileName.isEmpty()) fileName = file.getName();
                                    }
                                } catch (Exception ignored) {}
                            }

                            // Fallback to ContentResolver query via MediaStore if direct File access was restricted
                            if (inputStream == null) {
                                Cursor c = null;
                                try {
                                    Uri mediaUri = MediaStore.Files.getContentUri("external");
                                    c = getContentResolver().query(mediaUri, new String[]{MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.SIZE}, MediaStore.MediaColumns.DATA + "=?", new String[]{filePath}, null);
                                    if (c != null && c.moveToFirst()) {
                                        long id = c.getLong(c.getColumnIndex(MediaStore.MediaColumns._ID));
                                        int nameCol = c.getColumnIndex(MediaStore.MediaColumns.DISPLAY_NAME);
                                        int sizeCol = c.getColumnIndex(MediaStore.MediaColumns.SIZE);
                                        if (nameCol >= 0) fileName = c.getString(nameCol);
                                        if (sizeCol >= 0 && totalBytes <= 0) totalBytes = c.getLong(sizeCol);
                                        Uri contentUri = ContentUris.withAppendedId(mediaUri, id);
                                        inputStream = getContentResolver().openInputStream(contentUri);
                                    }
                                } catch (Exception ignored) {}
                                finally {
                                    if (c != null) c.close();
                                }
                            }
                        }

                        if (inputStream != null) {
                            inputStream = new java.io.BufferedInputStream(inputStream, 131072);
                        }

                        if (fileName == null || fileName.isEmpty()) {
                            int slash = filePath.lastIndexOf('/');
                            fileName = (slash >= 0) ? filePath.substring(slash + 1) : filePath;
                        }

                        if (inputStream == null) {
                            final String errName = fileName;
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    Toast.makeText(MainActivity.this, "Cannot access file on phone: " + errName, Toast.LENGTH_SHORT).show();
                                    if (webView != null) {
                                        webView.evaluateJavascript("if(window.onPhoneUploadError) window.onPhoneUploadError('" + filePath.replace("'", "\\'") + "', 'Access denied');", null);
                                    }
                                }
                            });
                            return;
                        }

                        final String finalFileName = fileName;
                        final long finalTotalBytes = totalBytes;
                        final String charset = "UTF-8";

                        // Sanitize serverUrl to prevent duplicate slashes and 307 redirect issues
                        String baseServer = (serverUrl != null) ? serverUrl.trim() : "";
                        while (baseServer.endsWith("/")) {
                            baseServer = baseServer.substring(0, baseServer.length() - 1);
                        }

                        // Check if file partially exists on PC to support instant resume
                        long resumeOffset = 0;
                        if (finalTotalBytes > 10485760) { // Check resume for files > 10MB
                            try {
                                String verifyUrl = baseServer + "/api/fs/verify?filename=" + java.net.URLEncoder.encode(fileName, charset);
                                if (pcDestDir != null && !pcDestDir.isEmpty()) {
                                    verifyUrl += "&dest_dir=" + java.net.URLEncoder.encode(pcDestDir, charset);
                                }
                                URL vUrl = new URL(verifyUrl);
                                HttpURLConnection vConn = (HttpURLConnection) vUrl.openConnection();
                                vConn.setConnectTimeout(800);
                                vConn.setReadTimeout(800);
                                if (vConn.getResponseCode() == 200) {
                                    java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(vConn.getInputStream()));
                                    StringBuilder sb = new StringBuilder();
                                    String line;
                                    while ((line = reader.readLine()) != null) sb.append(line);
                                    reader.close();
                                    JSONObject statObj = new JSONObject(sb.toString());
                                    if (statObj.optBoolean("exists", false)) {
                                        long remoteSize = statObj.optLong("size", 0);
                                        if (remoteSize > 0 && remoteSize < finalTotalBytes) {
                                            resumeOffset = remoteSize;
                                            long skipped = inputStream.skip(resumeOffset);
                                            if (skipped != resumeOffset) {
                                                resumeOffset = 0; // fallback to clean upload if skip failed
                                            }
                                        }
                                    }
                                }
                                vConn.disconnect();
                            } catch (Exception ignored) {}
                        }

                        // Stream directly to /api/fs/upload-stream for ultra-fast zero-tempfile transfer
                        String targetUrl = baseServer + "/api/fs/upload-stream?filename=" + java.net.URLEncoder.encode(fileName, charset);
                        if (pcDestDir != null && !pcDestDir.isEmpty()) {
                            targetUrl += "&dest_dir=" + java.net.URLEncoder.encode(pcDestDir, charset);
                        }
                        if (resumeOffset > 0) {
                            targetUrl += "&offset=" + resumeOffset;
                        }

                        URL url = new URL(targetUrl);
                        conn = (HttpURLConnection) url.openConnection();
                        conn.setUseCaches(false);
                        conn.setDoOutput(true);
                        conn.setDoInput(true);
                        conn.setInstanceFollowRedirects(false);
                        conn.setRequestMethod("POST");
                        conn.setRequestProperty("Connection", "Keep-Alive");
                        conn.setRequestProperty("Accept-Encoding", "identity");
                        conn.setRequestProperty("Content-Type", "application/octet-stream");
                        conn.setRequestProperty("X-File-Name", java.net.URLEncoder.encode(fileName, charset));
                        if (pcDestDir != null && !pcDestDir.isEmpty()) {
                            conn.setRequestProperty("X-Dest-Dir", java.net.URLEncoder.encode(pcDestDir, charset));
                        }
                        if (resumeOffset > 0) {
                            conn.setRequestProperty("X-File-Offset", String.valueOf(resumeOffset));
                        }
                        if (finalTotalBytes > 0) {
                            conn.setRequestProperty("X-File-Size", String.valueOf(finalTotalBytes));
                        }
                        conn.setRequestProperty("User-Agent", "PCDeckPro/2.1");
                        conn.setConnectTimeout(15000);
                        conn.setReadTimeout(30000); // 30s timeout preventing indefinite hangs

                        // Use 128KB Chunked Streaming Mode for steady throughput without buffer bloat
                        conn.setChunkedStreamingMode(131072);

                        final long initOffset = resumeOffset;
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (webView != null) {
                                    int startPercent = finalTotalBytes > 0 ? (int)((initOffset * 100) / finalTotalBytes) : 0;
                                    webView.evaluateJavascript("if(window.onPhoneUploadProgress) window.onPhoneUploadProgress(" + startPercent + ", " + initOffset + ", " + finalTotalBytes + ", '" + finalFileName.replace("'", "\\'") + "');", null);
                                }
                            }
                        });

                        outputStream = new java.io.BufferedOutputStream(conn.getOutputStream(), 131072);
                        byte[] buffer = new byte[131072]; // 128KB buffer
                        long totalRead = resumeOffset;
                        int bytesRead;
                        long startTime = System.currentTimeMillis();
                        long lastWebUpdate = startTime;
                        long lastNotifUpdate = startTime;

                        final boolean isPro = isProUser();
                        final long maxBytesPerSec = isPro ? 0 : 10485760L; // Free: 10 MB/s, Pro: Uncapped Turbo

                        while ((bytesRead = inputStream.read(buffer)) != -1) {
                            outputStream.write(buffer, 0, bytesRead);
                            totalRead += bytesRead;

                            if (maxBytesPerSec > 0) {
                                long bytesSent = totalRead - resumeOffset;
                                long expectedMs = (bytesSent * 1000L) / maxBytesPerSec;
                                long elapsedMs = System.currentTimeMillis() - startTime;
                                if (expectedMs > elapsedMs) {
                                    long sleepMs = expectedMs - elapsedMs;
                                    if (sleepMs > 0 && sleepMs <= 500) {
                                        try { Thread.sleep(sleepMs); } catch (InterruptedException ignored) {}
                                    }
                                }
                            }

                            long now = System.currentTimeMillis();
                            boolean isFinished = (finalTotalBytes > 0 && totalRead == finalTotalBytes);

                            if (now - lastWebUpdate > 250 || isFinished) {
                                lastWebUpdate = now;
                                final int percent = finalTotalBytes > 0 ? (int) ((totalRead * 100) / finalTotalBytes) : 0;
                                final long loaded = totalRead;
                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        if (webView != null) {
                                            webView.evaluateJavascript("if(window.onPhoneUploadProgress) window.onPhoneUploadProgress(" + percent + ", " + loaded + ", " + finalTotalBytes + ", '" + finalFileName.replace("'", "\\'") + "');", null);
                                        }
                                    }
                                });
                            }

                            if (now - lastNotifUpdate > 1200 || isFinished) {
                                lastNotifUpdate = now;
                                final int percent = finalTotalBytes > 0 ? (int) ((totalRead * 100) / finalTotalBytes) : 0;
                                final long loaded = totalRead;
                                double elapsedSec = (now - startTime) / 1000.0;
                                double speedMb = elapsedSec > 0.2 ? ((totalRead - resumeOffset) / 1048576.0) / elapsedSec : 0;
                                final String speedStr = speedMb > 0 ? String.format("%.1f MB/s", speedMb) : "--";

                                updateTransferNotification(
                                    "📤 Uploading " + fileName,
                                    percent + "% (" + formatSize(loaded) + " of " + formatSize(finalTotalBytes) + ") • " + speedStr,
                                    percent,
                                    true
                                );
                            }
                        }

                        outputStream.flush();
                        outputStream.close();
                        outputStream = null;

                        if (inputStream != null) {
                            inputStream.close();
                            inputStream = null;
                        }

                        final int responseCode = conn.getResponseCode();
                        final boolean success = (responseCode >= 200 && responseCode < 300);

                        long serverReportedSize = 0;
                        // Read response payload to verify exact bytes on PC
                        java.io.InputStream respStream = success ? conn.getInputStream() : conn.getErrorStream();
                        if (respStream != null) {
                            java.io.BufferedReader respReader = new java.io.BufferedReader(new java.io.InputStreamReader(respStream));
                            StringBuilder respSb = new StringBuilder();
                            String rLine;
                            while ((rLine = respReader.readLine()) != null) respSb.append(rLine);
                            respReader.close();
                            try {
                                JSONObject jsonResp = new JSONObject(respSb.toString());
                                serverReportedSize = jsonResp.optLong("size", 0);
                            } catch (Exception ignored) {}
                        }

                        final boolean verified = (finalTotalBytes <= 0 || serverReportedSize == finalTotalBytes || totalRead == finalTotalBytes);

                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (success) {
                                    updateTransferNotification("✅ Upload Verified & Complete", "Saved " + finalFileName + " (" + formatSize(finalTotalBytes) + ") to PC", 100, false);
                                    Toast.makeText(MainActivity.this, "Uploaded " + finalFileName + (verified ? " (Verified)" : ""), Toast.LENGTH_SHORT).show();
                                    if (webView != null) {
                                        webView.evaluateJavascript("if(window.onPhoneUploadComplete) window.onPhoneUploadComplete('" + finalFileName.replace("'", "\\'") + "', " + verified + ");", null);
                                    }
                                } else {
                                    updateTransferNotification("❌ Upload Failed", "HTTP " + responseCode + " on " + finalFileName, 0, false);
                                    Toast.makeText(MainActivity.this, "Upload failed (HTTP " + responseCode + ")", Toast.LENGTH_SHORT).show();
                                    if (webView != null) {
                                        webView.evaluateJavascript("if(window.onPhoneUploadError) window.onPhoneUploadError('" + finalFileName.replace("'", "\\'") + "', 'HTTP " + responseCode + "');", null);
                                    }
                                }
                            }
                        });
                    } catch (final Exception e) {
                        updateTransferNotification("❌ Upload Failed", "Error on " + fileName + ": " + e.getMessage(), 0, false);
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(MainActivity.this, "Upload error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                                if (webView != null) {
                                    webView.evaluateJavascript("if(window.onPhoneUploadError) window.onPhoneUploadError('" + filePath.replace("'", "\\'") + "', '" + e.getMessage().replace("'", "\\'") + "');", null);
                                }
                            }
                        });
                    } finally {
                        releaseTransferLocks();
                        try { if (inputStream != null) inputStream.close(); } catch (Exception ignored) {}
                        try { if (outputStream != null) outputStream.close(); } catch (Exception ignored) {}
                        try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
                    }
                }
            }).start();
        }

        @JavascriptInterface
        public boolean isAccessibilityEnabled() {
            return NeonTrackAccessibilityService.isRunning();
        }

        @JavascriptInterface
        public void openAccessibilitySettings() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Intent intent = new Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS);
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(intent);
                        Toast.makeText(MainActivity.this, "Please enable 'PCDeck Pro' in Accessibility to allow PC control", Toast.LENGTH_LONG).show();
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Cannot open Accessibility Settings: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }

        @JavascriptInterface
        public boolean dispatchPhoneTap(float x, float y) {
            NeonTrackAccessibilityService service = NeonTrackAccessibilityService.getInstance();
            if (service != null) {
                return service.performTap(x, y);
            }
            return false;
        }

        @JavascriptInterface
        public boolean dispatchPhoneSwipe(float x1, float y1, float x2, float y2, long duration) {
            NeonTrackAccessibilityService service = NeonTrackAccessibilityService.getInstance();
            if (service != null) {
                return service.performSwipe(x1, y1, x2, y2, duration);
            }
            return false;
        }

        @JavascriptInterface
        public boolean dispatchPhoneNav(String action) {
            NeonTrackAccessibilityService service = NeonTrackAccessibilityService.getInstance();
            if (service != null) {
                return service.performNav(action);
            }
            return false;
        }

        @JavascriptInterface
        public boolean dispatchPhoneText(String text) {
            NeonTrackAccessibilityService service = NeonTrackAccessibilityService.getInstance();
            if (service != null) {
                return service.typeText(text);
            }
            return false;
        }

        @JavascriptInterface
        public void showSoftKeyboard() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (webView != null) {
                        webView.requestFocus();
                        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            imm.showSoftInput(webView, InputMethodManager.SHOW_IMPLICIT);
                        }
                    }
                }
            });
        }

        @JavascriptInterface
        public void hideSoftKeyboard() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (webView != null) {
                        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            imm.hideSoftInputFromWindow(webView.getWindowToken(), 0);
                        }
                    }
                }
            });
        }

        @JavascriptInterface
        public void setImmersiveFullscreen(final boolean enable) {
            applyImmersiveFullscreen();
        }

        @JavascriptInterface
        public void requestFullscreen() {
            applyImmersiveFullscreen();
        }

        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(intent);
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Could not open URL: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        createNotificationChannel();
        if (Build.VERSION.SDK_INT >= 33) { // Android 13+ TIRAMISU
            try {
                if (checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, NOTIF_PERMISSION_REQUEST);
                }
            } catch (Exception ignored) {}
        }

        // Keep screen awake while using trackpad/screen controller
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // Allow drawing into notch cutout area in landscape mode (Android P / API 28+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            getWindow().getAttributes().layoutInDisplayCutoutMode =
                WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        // Apply true edge-to-edge immersive fullscreen (hiding status bar, battery, time, nav bar)
        applyImmersiveFullscreen();

        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);

        // Disable strict mode death on file uri exposure for seamless third-party app viewing
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            try {
                java.lang.reflect.Method m = android.os.StrictMode.class.getMethod("disableDeathOnFileUriExposure");
                m.invoke(null);
            } catch (Exception ignored) {}
        }

        setupWebView();

        // Check if launched via Universal Connect deep link (e.g. https://pcdeck.vercel.app/connect?ip=...)
        String initialUrl = "file:///android_asset/index.html";
        Uri intentData = getIntent() != null ? getIntent().getData() : null;
        if (intentData != null) {
            String ipParam = intentData.getQueryParameter("ip");
            if (ipParam != null && !ipParam.isEmpty()) {
                initialUrl += "?ip=" + Uri.encode(ipParam);
            }
        }

        // Start zero-config UDP background discovery for instant connection
        startUdpDiscovery();

        // Load local bundled web assets with full UI
        webView.loadUrl(initialUrl);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent != null && intent.getData() != null) {
            String ipParam = intent.getData().getQueryParameter("ip");
            if (ipParam != null && !ipParam.isEmpty()) {
                final String cleanIp = ipParam;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (webView != null) {
                            webView.evaluateJavascript("if (window.parseQrAndConnect) { window.parseQrAndConnect('" + cleanIp + "'); }", null);
                        }
                    }
                });
            }
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        webView.clearCache(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        // Ensure webview can receive keyboard and touch input focus
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        // Enable hardware acceleration
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        webView.setBackgroundColor(Color.parseColor("#0a0e17"));
        webView.setLongClickable(false);
        webView.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                return true;
            }
        });

        // Register JS interface for hardware/native control
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidApp");

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                            if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                                    request.grant(request.getResources());
                                }
                            } else {
                                mPendingCameraPermissionRequest = request;
                                requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
                            }
                        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                            request.grant(request.getResources());
                        }
                    }
                });
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (mUploadMessage != null) {
                    mUploadMessage.onReceiveValue(null);
                    mUploadMessage = null;
                }
                mUploadMessage = filePathCallback;

                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(intent, "Select File to Send to PC"), FILE_CHOOSER_REQUEST);
                } catch (Exception e) {
                    mUploadMessage = null;
                    Toast.makeText(MainActivity.this, "Cannot open file picker", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });

        // Handle file downloads directly via DownloadManager
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimetype, long contentLength) {
                try {
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                    String filename = URLUtil.guessFileName(url, contentDisposition, mimetype);
                    request.setTitle(filename);
                    request.setDescription("Downloading file from PC...");
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);

                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    if (dm != null) {
                        dm.enqueue(request);
                        Toast.makeText(MainActivity.this, "Downloading " + filename + " to Downloads folder", Toast.LENGTH_SHORT).show();
                    }
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Download error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (mUploadMessage == null) return;
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && data != null) {
                String dataString = data.getDataString();
                if (dataString != null) {
                    results = new Uri[]{Uri.parse(dataString)};
                } else if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    results = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        results[i] = data.getClipData().getItemAt(i).getUri();
                    }
                }
            }
            mUploadMessage.onReceiveValue(results);
            mUploadMessage = null;
        }
    }

    public void applyImmersiveFullscreen() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                        WindowInsetsController insetsController = getWindow().getInsetsController();
                        if (insetsController != null) {
                            insetsController.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                            insetsController.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                        }
                    } else {
                        View decorView = getWindow().getDecorView();
                        int flags = View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                                  | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                                  | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                                  | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                                  | View.SYSTEM_UI_FLAG_FULLSCREEN
                                  | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY;
                        decorView.setSystemUiVisibility(flags);
                    }
                } catch (Exception e) {
                    getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
                }
            }
        });
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            applyImmersiveFullscreen();
        }
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        applyImmersiveFullscreen();
        if (webView != null) {
            String orientation = (newConfig.orientation == Configuration.ORIENTATION_LANDSCAPE) ? "landscape" : "portrait";
            webView.evaluateJavascript("window.onScreenOrientationChange && window.onScreenOrientationChange('" + orientation + "');", null);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                if (mPendingCameraPermissionRequest != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    mPendingCameraPermissionRequest.grant(mPendingCameraPermissionRequest.getResources());
                    mPendingCameraPermissionRequest = null;
                }
            } else {
                if (mPendingCameraPermissionRequest != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    mPendingCameraPermissionRequest.deny();
                    mPendingCameraPermissionRequest = null;
                }
                Toast.makeText(this, "Camera permission is needed to scan PC QR code", Toast.LENGTH_SHORT).show();
            }
        } else if (requestCode == STORAGE_PERMISSION_REQUEST) {
            boolean anyGranted = false;
            for (int res : grantResults) {
                if (res == PackageManager.PERMISSION_GRANTED) {
                    anyGranted = true;
                    break;
                }
            }
            if (anyGranted) {
                Toast.makeText(this, "Storage access granted", Toast.LENGTH_SHORT).show();
            }
            if (webView != null) {
                webView.evaluateJavascript("if(window.onStoragePermissionChanged) window.onStoragePermissionChanged();", null);
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        startUdpDiscovery();
        if (webView != null) {
            webView.evaluateJavascript("if(window.onAppResume) window.onAppResume(); if(window.onStoragePermissionChanged) window.onStoragePermissionChanged();", null);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
