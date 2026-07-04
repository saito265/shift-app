/*
 * kintoneポータルにシフト管理アプリを埋め込むカスタマイズ
 * アップロード先: kintoneシステム管理 > JavaScript / CSSでカスタマイズ > PC用のJavaScriptファイル
 */
(function () {
  'use strict';

  // シフトアプリのURL（?embed=true でStreamlitのメニュー等を隠したスッキリ表示になる）
  var APP_URL = 'https://shift-app-cd4xjrsugd4bzwze8rc9qk.streamlit.app/?embed=true';
  var FRAME_ID = 'shift-app-frame';
  var FRAME_HEIGHT = '950px';

  function isPortalPage() {
    // ポータル（トップページ）のときだけ表示する
    var h = location.hash;
    return location.pathname.indexOf('/k/') === 0 &&
      (h === '' || h === '#/' || h.indexOf('#/portal') === 0);
  }

  function insertFrame() {
    var existing = document.getElementById(FRAME_ID);
    if (!isPortalPage()) {
      // ポータル以外の画面に移動したら消す
      if (existing) existing.parentNode.removeChild(existing.parentNode ? existing : existing);
      return;
    }
    if (existing) return; // すでに表示済み

    // ポータルの本文エリアを探す（kintoneの画面構造の違いに備えて複数候補）
    var container =
      document.querySelector('.ocean-portal-body') ||
      document.querySelector('.ocean-portal-content') ||
      document.querySelector('.gaia-argoui-space-spacelayout-body') ||
      document.querySelector('#contents-body') ||
      document.querySelector('#contents');
    if (!container) return;

    var wrap = document.createElement('div');
    wrap.id = FRAME_ID;
    wrap.style.cssText = 'margin:8px 0 16px;';
    wrap.innerHTML =
      '<div style="font-weight:bold;font-size:14px;margin:4px 0;">📅 カトカミ シフト管理</div>' +
      '<iframe src="' + APP_URL + '" ' +
      'style="width:100%;height:' + FRAME_HEIGHT + ';border:1px solid #ddd;border-radius:8px;background:#fff;" ' +
      'loading="lazy"></iframe>';
    container.insertBefore(wrap, container.firstChild);
  }

  // 画面の描画・切り替えを監視して差し込む（kintoneは画面遷移してもページを読み直さないため）
  var observer = new MutationObserver(insertFrame);
  observer.observe(document.body, { childList: true, subtree: true });
  insertFrame();
})();
