package com.neontrack.mouse;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Path;
import android.os.Build;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

public class NeonTrackAccessibilityService extends AccessibilityService {

    private static NeonTrackAccessibilityService instance;

    @Override
    public void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // No custom event processing needed
    }

    @Override
    public void onInterrupt() {
        // Service interrupted
    }

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        instance = null;
        return super.onUnbind(intent);
    }

    public static NeonTrackAccessibilityService getInstance() {
        return instance;
    }

    public static boolean isRunning() {
        return instance != null;
    }

    /**
     * Dispatch single tap gesture at (x, y) coordinates.
     */
    public boolean performTap(float x, float y) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            Path path = new Path();
            path.moveTo(x, y);
            GestureDescription.Builder builder = new GestureDescription.Builder();
            GestureDescription.StrokeDescription stroke = new GestureDescription.StrokeDescription(path, 0, 50);
            builder.addStroke(stroke);
            return dispatchGesture(builder.build(), null, null);
        }
        return false;
    }

    /**
     * Dispatch swipe / drag gesture from (x1, y1) to (x2, y2).
     */
    public boolean performSwipe(float x1, float y1, float x2, float y2, long duration) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            Path path = new Path();
            path.moveTo(x1, y1);
            path.lineTo(x2, y2);
            GestureDescription.Builder builder = new GestureDescription.Builder();
            GestureDescription.StrokeDescription stroke = new GestureDescription.StrokeDescription(path, 0, Math.max(50, duration));
            builder.addStroke(stroke);
            return dispatchGesture(builder.build(), null, null);
        }
        return false;
    }

    /**
     * Execute system navigation global actions (Back, Home, Recents, Lock, Notifications).
     */
    public boolean performNav(String action) {
        if (action == null) return false;
        String act = action.trim().toLowerCase();

        switch (act) {
            case "back":
                return performGlobalAction(GLOBAL_ACTION_BACK);
            case "home":
                return performGlobalAction(GLOBAL_ACTION_HOME);
            case "recents":
                return performGlobalAction(GLOBAL_ACTION_RECENTS);
            case "notifications":
                return performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS);
            case "quick_settings":
                return performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS);
            case "lock":
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    return performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
                } else {
                    return performGlobalAction(GLOBAL_ACTION_POWER_DIALOG);
                }
            case "power":
                return performGlobalAction(GLOBAL_ACTION_POWER_DIALOG);
            default:
                return false;
        }
    }

    /**
     * Insert or paste text into the active focused input node on screen.
     */
    public boolean typeText(String text) {
        if (text == null) return false;
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root == null) return false;

            AccessibilityNodeInfo focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
            if (focusedNode == null) {
                focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY);
            }

            if (focusedNode != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    Bundle arguments = new Bundle();
                    CharSequence existingText = focusedNode.getText();
                    String newText = (existingText != null ? existingText.toString() : "") + text;
                    arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, newText);
                    boolean setSuccess = focusedNode.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
                    if (setSuccess) return true;
                }

                // Fallback: Copy to clipboard and perform paste action
                ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                if (clipboard != null) {
                    ClipData clip = ClipData.newPlainText("neontrack_text", text);
                    clipboard.setPrimaryClip(clip);
                    return focusedNode.performAction(AccessibilityNodeInfo.ACTION_PASTE);
                }
            }
        } catch (Exception e) {
            // Silently handle
        }
        return false;
    }
}
