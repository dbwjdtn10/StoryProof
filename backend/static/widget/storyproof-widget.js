/**
 * StoryProof 임베드 챗봇 위젯 v1
 * ==============================
 * 파트너 사이트(뷰어/상세페이지)에 한 줄로 삽입하는 작품 Q&A 챗봇.
 *
 * 사용법 (자동 초기화):
 *   <script src="https://<storyproof-host>/static/widget/storyproof-widget.js"
 *           data-token="<위젯 세션 토큰>"
 *           data-title="달빛 조각사"          (선택)
 *           data-color="#4F46E5"             (선택)
 *           data-position="right"></script>  (선택: right|left)
 *
 * 프로그래매틱 초기화:
 *   StoryProofWidget.init({ token, apiBase, title, color, position });
 *
 * 보안:
 * - 파트너 API 키는 절대 이 위젯에 넣지 않는다. 파트너 서버가
 *   POST /api/partner/v1/widget-sessions 로 발급한 단기 세션 토큰만 사용.
 * - 토큰에는 작품/회차 범위가 고정되어 있어 다른 작품은 조회 불가.
 * - Shadow DOM으로 호스트 페이지 CSS와 완전 격리.
 */
(function () {
    'use strict';

    if (window.StoryProofWidget && window.StoryProofWidget._mounted) return;

    var STATE = {
        config: null,
        open: false,
        busy: false,
        host: null,
        els: {},
    };

    function detectApiBase() {
        // 이 스크립트를 로드한 origin을 기본 API 서버로 사용
        var script = document.currentScript;
        if (script && script.src) {
            try { return new URL(script.src).origin; } catch (e) { /* fallthrough */ }
        }
        return window.location.origin;
    }

    function buildStyles(color) {
        return '\n' +
            ':host { all: initial; }\n' +
            '* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; }\n' +
            '.sp-fab { position: fixed; bottom: 24px; width: 56px; height: 56px; border-radius: 50%;\n' +
            '  background: ' + color + '; color: #fff; border: none; cursor: pointer; font-size: 24px;\n' +
            '  box-shadow: 0 4px 16px rgba(0,0,0,.25); z-index: 2147483000; display: flex; align-items: center; justify-content: center;\n' +
            '  transition: transform .15s; }\n' +
            '.sp-fab:hover { transform: scale(1.06); }\n' +
            '.sp-panel { position: fixed; bottom: 92px; width: 340px; max-width: calc(100vw - 32px); height: 480px;\n' +
            '  max-height: calc(100vh - 120px); background: #fff; border-radius: 16px; z-index: 2147483000;\n' +
            '  box-shadow: 0 8px 32px rgba(0,0,0,.28); display: none; flex-direction: column; overflow: hidden; }\n' +
            '.sp-panel.open { display: flex; }\n' +
            '.sp-header { background: ' + color + '; color: #fff; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; }\n' +
            '.sp-header .sp-title { font-size: 14px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }\n' +
            '.sp-header .sp-sub { font-size: 11px; opacity: .85; margin-top: 2px; }\n' +
            '.sp-close { background: none; border: none; color: #fff; font-size: 18px; cursor: pointer; padding: 4px; }\n' +
            '.sp-msgs { flex: 1; overflow-y: auto; padding: 14px; background: #F8F7F5; }\n' +
            '.sp-msg { max-width: 85%; padding: 9px 12px; border-radius: 12px; font-size: 13px; line-height: 1.5;\n' +
            '  margin-bottom: 8px; white-space: pre-wrap; word-break: break-word; }\n' +
            '.sp-msg.user { background: ' + color + '; color: #fff; margin-left: auto; border-bottom-right-radius: 4px; }\n' +
            '.sp-msg.bot { background: #fff; color: #1c1917; border: 1px solid #e7e5e4; border-bottom-left-radius: 4px; }\n' +
            '.sp-msg.error { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }\n' +
            '.sp-hint { font-size: 11px; color: #a8a29e; text-align: center; margin: 8px 0; }\n' +
            '.sp-typing { display: inline-flex; gap: 4px; padding: 12px; }\n' +
            '.sp-typing span { width: 6px; height: 6px; border-radius: 50%; background: #a8a29e; animation: sp-blink 1.2s infinite; }\n' +
            '.sp-typing span:nth-child(2) { animation-delay: .2s; }\n' +
            '.sp-typing span:nth-child(3) { animation-delay: .4s; }\n' +
            '@keyframes sp-blink { 0%, 80%, 100% { opacity: .3; } 40% { opacity: 1; } }\n' +
            '.sp-inputbar { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #e7e5e4; background: #fff; }\n' +
            '.sp-input { flex: 1; border: 1px solid #d6d3d1; border-radius: 10px; padding: 9px 12px; font-size: 13px; outline: none; }\n' +
            '.sp-input:focus { border-color: ' + color + '; }\n' +
            '.sp-send { background: ' + color + '; color: #fff; border: none; border-radius: 10px; padding: 0 14px;\n' +
            '  cursor: pointer; font-size: 13px; font-weight: 600; }\n' +
            '.sp-send:disabled { opacity: .5; cursor: not-allowed; }\n' +
            '.sp-brand { font-size: 10px; color: #d6d3d1; text-align: center; padding: 4px 0 6px; background: #fff; }\n';
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }

    function addMessage(kind, text) {
        var msg = el('div', 'sp-msg ' + kind, text);
        STATE.els.msgs.appendChild(msg);
        STATE.els.msgs.scrollTop = STATE.els.msgs.scrollHeight;
        return msg;
    }

    function showTyping() {
        var wrap = el('div', 'sp-msg bot');
        var typing = el('div', 'sp-typing');
        typing.appendChild(el('span'));
        typing.appendChild(el('span'));
        typing.appendChild(el('span'));
        wrap.appendChild(typing);
        STATE.els.msgs.appendChild(wrap);
        STATE.els.msgs.scrollTop = STATE.els.msgs.scrollHeight;
        return wrap;
    }

    function errorMessageFor(status) {
        if (status === 401) return '세션이 만료되었습니다. 페이지를 새로고침해주세요.';
        if (status === 429) return '요청이 많아 잠시 제한되었습니다. 잠시 후 다시 시도해주세요.';
        return '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
    }

    function ask(question) {
        if (STATE.busy || !question.trim()) return;
        STATE.busy = true;
        STATE.els.send.disabled = true;
        addMessage('user', question);
        STATE.els.input.value = '';
        var typing = showTyping();

        fetch(STATE.config.apiBase + '/api/widget/v1/qa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + STATE.config.token,
            },
            body: JSON.stringify({ question: question }),
        }).then(function (res) {
            if (!res.ok) throw { status: res.status };
            return res.json();
        }).then(function (data) {
            typing.remove();
            if (data.found_context) {
                addMessage('bot', data.answer);
            } else {
                addMessage('bot', data.answer || '작품에서 관련 내용을 찾지 못했어요. 다른 질문을 해보세요!');
            }
        }).catch(function (err) {
            typing.remove();
            addMessage('error', errorMessageFor(err && err.status));
        }).finally(function () {
            STATE.busy = false;
            STATE.els.send.disabled = false;
            STATE.els.input.focus();
        });
    }

    function loadMeta() {
        // data-title 미지정 시 서버에서 작품 제목 조회
        if (STATE.config.title) return;
        fetch(STATE.config.apiBase + '/api/widget/v1/meta', {
            headers: { 'Authorization': 'Bearer ' + STATE.config.token },
        }).then(function (res) { return res.ok ? res.json() : null; })
          .then(function (meta) {
              if (meta && meta.title) STATE.els.title.textContent = meta.title;
          }).catch(function () { /* 제목은 장식 — 실패 무시 */ });
    }

    function togglePanel(open) {
        STATE.open = (typeof open === 'boolean') ? open : !STATE.open;
        STATE.els.panel.classList.toggle('open', STATE.open);
        STATE.els.fab.textContent = STATE.open ? '✕' : '💬';
        if (STATE.open) STATE.els.input.focus();
    }

    function mount(config) {
        var host = document.createElement('div');
        host.id = 'storyproof-widget-host';
        document.body.appendChild(host);
        var root = host.attachShadow({ mode: 'closed' });

        var style = document.createElement('style');
        style.textContent = buildStyles(config.color);
        root.appendChild(style);

        var side = (config.position === 'left') ? 'left: 24px;' : 'right: 24px;';

        var fab = el('button', 'sp-fab', '💬');
        fab.setAttribute('style', side);
        fab.setAttribute('aria-label', '작품 챗봇 열기');
        fab.addEventListener('click', function () { togglePanel(); });

        var panel = el('div', 'sp-panel');
        panel.setAttribute('style', side);

        var header = el('div', 'sp-header');
        var headText = el('div');
        var title = el('div', 'sp-title', config.title || '작품 도우미');
        headText.appendChild(title);
        headText.appendChild(el('div', 'sp-sub', '읽은 부분까지만 답해드려요'));
        var close = el('button', 'sp-close', '✕');
        close.setAttribute('aria-label', '닫기');
        close.addEventListener('click', function () { togglePanel(false); });
        header.appendChild(headText);
        header.appendChild(close);

        var msgs = el('div', 'sp-msgs');
        msgs.appendChild(el('div', 'sp-hint', '이 작품에 대해 무엇이든 물어보세요'));

        var inputbar = el('div', 'sp-inputbar');
        var input = el('input', 'sp-input');
        input.setAttribute('placeholder', '예: 주인공이 왜 길드를 떠났어?');
        input.setAttribute('maxlength', '2000');
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.isComposing) ask(input.value);
            if (e.key === 'Escape') togglePanel(false);
        });
        var send = el('button', 'sp-send', '전송');
        send.addEventListener('click', function () { ask(input.value); });
        inputbar.appendChild(input);
        inputbar.appendChild(send);

        panel.appendChild(header);
        panel.appendChild(msgs);
        panel.appendChild(inputbar);
        panel.appendChild(el('div', 'sp-brand', 'powered by StoryProof'));

        root.appendChild(fab);
        root.appendChild(panel);

        STATE.host = host;
        STATE.els = { fab: fab, panel: panel, msgs: msgs, input: input, send: send, title: title };
        loadMeta();

        // 첫 인사
        addMessage('bot', '안녕하세요! 이 작품에 대해 궁금한 점을 물어보세요. 아직 읽지 않은 부분은 스포일러 방지를 위해 답하지 않아요.');
    }

    var api = {
        _mounted: false,
        init: function (config) {
            if (api._mounted) return;
            if (!config || !config.token) {
                console.error('[StoryProofWidget] token이 필요합니다.');
                return;
            }
            STATE.config = {
                token: config.token,
                apiBase: (config.apiBase || detectApiBase()).replace(/\/$/, ''),
                title: config.title || '',
                color: config.color || '#4F46E5',
                position: config.position === 'left' ? 'left' : 'right',
            };
            api._mounted = true;
            if (document.body) mount(STATE.config);
            else document.addEventListener('DOMContentLoaded', function () { mount(STATE.config); });
        },
        open: function () { if (api._mounted) togglePanel(true); },
        close: function () { if (api._mounted) togglePanel(false); },
        destroy: function () {
            if (STATE.host) STATE.host.remove();
            api._mounted = false;
            STATE.host = null;
        },
    };

    window.StoryProofWidget = api;

    // <script> 태그 data 속성으로 자동 초기화
    var script = document.currentScript;
    if (script && script.dataset && script.dataset.token) {
        api.init({
            token: script.dataset.token,
            apiBase: script.dataset.apiBase,
            title: script.dataset.title,
            color: script.dataset.color,
            position: script.dataset.position,
        });
    }
})();
