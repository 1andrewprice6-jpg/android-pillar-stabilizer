package com.christ3d

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.WindowInsetsController
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Full-screen immersive mode
        hideSystemUI()

        webView = WebView(this)
        setContentView(webView)

        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.mediaPlaybackRequiresUserGesture = false
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.loadWithOverviewMode = true
        settings.useWideViewPort = true
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false
        // Allow mixed content so the CDN Three.js loads from http if needed
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        webView.setBackgroundColor(Color.BLACK)

        webView.webViewClient = object : WebViewClient() {
            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError
            ) {
                // Non-fatal: assets will degrade gracefully if CDN is unreachable
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            // Allow full-screen video / canvas
            private var customView: View? = null
            private var customViewCallback: CustomViewCallback? = null

            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                customView = view
                customViewCallback = callback
                val container = window.decorView as FrameLayout
                container.addView(view)
                hideSystemUI()
            }

            override fun onHideCustomView() {
                val container = window.decorView as FrameLayout
                customView?.let { container.removeView(it) }
                customView = null
                customViewCallback?.onCustomViewHidden()
                hideSystemUI()
            }
        }

        // Load game from assets
        webView.loadUrl("file:///android_asset/game.html")
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemUI()
    }

    private fun hideSystemUI() {
        val controller = window.insetsController
        controller?.hide(
            android.view.WindowInsets.Type.statusBars() or
                    android.view.WindowInsets.Type.navigationBars()
        )
        controller?.systemBarsBehavior =
            WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
        hideSystemUI()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
