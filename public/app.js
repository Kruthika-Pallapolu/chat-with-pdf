
/**
 * CWP — Chat with PDF Web Frontend Application
 * PDF Intelligence Workspace Frontend Implementation
 */

document.addEventListener('DOMContentLoaded', () => {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = async (...args) => {
        const response = await nativeFetch(...args);
        if (response.status === 401 && new URL(args[0], window.location.href).pathname.startsWith('/api/')) {
            window.location.reload();
        }
        return response;
    };

    // --------------------------------------------------------------------------
    // 1. DOM Elements Selection
    // --------------------------------------------------------------------------

    // App Root & Modals
    const appRoot = document.getElementById('appRoot');
    const authModal = document.getElementById('authModal');
    const settingsModal = document.getElementById('settingsModal');
    const changePasswordModal = document.getElementById('changePasswordModal');
    const confirmRemoveModal = document.getElementById('confirmRemoveModal');

    // Auth Forms & Inputs
    const signInForm = document.getElementById('signInForm');
    const signUpForm = document.getElementById('signUpForm');
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const authTitle = document.getElementById('authTitle');
    const authSubtitle = document.getElementById('authSubtitle');
    const authAlert = document.getElementById('authAlert');

    const btnGoSignUp = document.getElementById('btnGoSignUp');
    const btnGoSignIn = document.getElementById('btnGoSignIn');
    const btnGoForgot = document.getElementById('btnGoForgot');
    const btnGoSignInFromForgot = document.getElementById('btnGoSignInFromForgot');
    const btnSignInSubmit = document.getElementById('btnSignInSubmit');
    const btnSignUpSubmit = document.getElementById('btnSignUpSubmit');
    const btnForgotSubmit = document.getElementById('btnForgotSubmit');

    // Change Password Dedicated Modal Elements
    const btnOpenChangePassword = document.getElementById('btnOpenChangePassword');
    const btnCloseChangePwd = document.getElementById('btnCloseChangePwd');
    const verifyCurrPasswordForm = document.getElementById('verifyCurrPasswordForm');
    const setNewPasswordForm = document.getElementById('setNewPasswordForm');
    const changePasswordTitle = document.getElementById('changePasswordTitle');
    const changePasswordSubtitle = document.getElementById('changePasswordSubtitle');
    const changePwdAlert = document.getElementById('changePwdAlert');
    const btnForgotFromChangePassword = document.getElementById('btnForgotFromChangePassword');

    // Workspace & View Modes
    const workspaceContainer = document.getElementById('workspaceContainer');
    const viewModeToggleBtns = document.querySelectorAll('.view-mode-toggle .mode-btn');
    const pdfPanel = document.getElementById('pdfPanel');
    const chatPanel = document.getElementById('chatPanel');

    // PDF Viewer Controls
    const btnPdfPrev = document.getElementById('btnPdfPrev');
    const btnPdfNext = document.getElementById('btnPdfNext');
    const pdfPageNumInput = document.getElementById('pdfPageNumInput');
    const pdfPageTotal = document.getElementById('pdfPageTotal');
    const pdfViewerTitle = document.getElementById('pdfViewerTitle');
    const btnPdfZoomOut = document.getElementById('btnPdfZoomOut');
    const btnPdfZoomIn = document.getElementById('btnPdfZoomIn');
    const btnPdfFitWidth = document.getElementById('btnPdfFitWidth');
    const pdfZoomLabel = document.getElementById('pdfZoomLabel');
    const pdfEmptyState = document.getElementById('pdfEmptyState');
    const pdfCanvasWrapper = document.getElementById('pdfCanvasWrapper');
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pdfTextHighlightOverlay = document.getElementById('pdfTextHighlightOverlay');
    const pdfViewerStage = document.getElementById('pdfViewerStage');

    // Header Controls & User Profile
    const systemStatusEl = document.getElementById('systemStatus');
    const statusTextEl = document.getElementById('statusText');
    const headerDocIndicator = document.getElementById('headerDocIndicator');
    const headerDocName = document.getElementById('headerDocName');
    const btnUserMenu = document.getElementById('btnUserMenu');
    const userAvatarText = document.getElementById('userAvatarText');
    const userMenuDropdown = document.getElementById('userMenuDropdown');
    const dropdownUserName = document.getElementById('dropdownUserName');
    const dropdownUserEmail = document.getElementById('dropdownUserEmail');
    const btnDropdownSettings = document.getElementById('btnDropdownSettings');
    const btnDropdownSignOut = document.getElementById('btnDropdownSignOut');
    const btnToggleSidebarMobile = document.getElementById('btnToggleSidebarMobile');

    // Sidebar & Navigation
    const sidebarPanel = document.getElementById('sidebarPanel');
    const btnNewChat = document.getElementById('btnNewChat');
    const chatHistoryList = document.getElementById('chatHistoryList');
    const btnSidebarSettings = document.getElementById('btnSidebarSettings');

    // Document Control (Sidebar & Settings)
    const dropZone = document.getElementById('dropZone');
    const pdfLoadedZone = document.getElementById('pdfLoadedZone');
    const loadedDocFilename = document.getElementById('loadedDocFilename');
    const pdfFileInput = document.getElementById('pdfFileInput');
    const btnRemovePdf = document.getElementById('btnRemovePdf');
    const btnConfirmRemoveDoc = document.getElementById('btnConfirmRemoveDoc');
    const btnCancelRemoveDoc = document.getElementById('btnCancelRemoveDoc');
    const confirmDocName = document.getElementById('confirmDocName');

    // Chat Interface & Toolbar
    const chatMessages = document.getElementById('chatMessages');
    const welcomeCard = document.getElementById('welcomeCard');
    const welcomeTitle = document.getElementById('welcomeTitle');
    const welcomeSubtitle = document.getElementById('welcomeSubtitle');
    const welcomeSuggestions = document.getElementById('welcomeSuggestions');
    const suggestionsList = document.getElementById('suggestionsList');
    const alertBanner = document.getElementById('alertBanner');
    const alertText = document.getElementById('alertText');
    const alertCloseBtn = document.getElementById('alertCloseBtn');

    const chatForm = document.getElementById('chatForm');
    const questionInput = document.getElementById('questionInput');
    const btnSubmit = document.getElementById('btnSubmit');

    const btnAttach = document.getElementById('btnAttach');
    const imageFileInput = document.getElementById('imageFileInput');
    const attachmentPreview = document.getElementById('attachmentPreview');
    const attachmentImg = document.getElementById('attachmentImg');
    const attachmentName = document.getElementById('attachmentName');
    const attachmentSize = document.getElementById('attachmentSize');
    const btnRemoveAttachment = document.getElementById('btnRemoveAttachment');
    const btnMic = document.getElementById('btnMic');
    const micBtnText = document.getElementById('micBtnText');
    const voiceRecordingBar = document.getElementById('voiceRecordingBar');
    const voiceStatusText = document.getElementById('voiceStatusText');
    const voiceFinalText = document.getElementById('voiceFinalText');
    const voiceInterimText = document.getElementById('voiceInterimText');
    const btnVoiceDone = document.getElementById('btnVoiceDone');
    const btnVoiceCancel = document.getElementById('btnVoiceCancel');

    let speechBaseText = '';
    let speechFinalText = '';

    // Settings Modal Tabs & Inputs
    const btnCloseSettings = document.getElementById('btnCloseSettings');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const themeSelectRadios = document.querySelectorAll('input[name="themeSelect"]');

    const settingsDocName = document.getElementById('settingsDocName');
    const settingsDocStatus = document.getElementById('settingsDocStatus');
    const btnSettingsUpload = document.getElementById('btnSettingsUpload');
    const btnSettingsRemove = document.getElementById('btnSettingsRemove');

    const settingsAvatar = document.getElementById('settingsAvatar');
    const settingsProfileName = document.getElementById('settingsProfileName');
    const settingsProfileEmail = document.getElementById('settingsProfileEmail');
    const btnSettingsSignOut = document.getElementById('btnSettingsSignOut');

    // Source Highlight Color Elements
    const colorSwatchBtns = document.querySelectorAll('.color-swatch-btn');
    const customColorPicker = document.getElementById('customColorPicker');
    const highlightPreviewMark = document.getElementById('highlightPreviewMark');

    // --------------------------------------------------------------------------
    // 2. Application State Store
    // --------------------------------------------------------------------------

    let supabaseClient = null;
    let currentSession = null;
    let currentDocument = null;
    let currentViewMode = 'split'; // 'pdf', 'chat', 'split'
    let currentHighlightColor = localStorage.getItem('cwp_highlight_color') || '#fde047';
let skipAutoRender = false;
        let documentRevision = 0;
        let pdfUploadInProgress = false;

    // PDF.js State
    let pdfDoc = null;
    let pdfCurrentPage = 1;
    let pdfTotalPages = 1;
    let pdfZoomScale = 1.0;
    let pdfRendering = false;
    let pdfPendingPage = null;
let pdfPendingHighlight = null;
let citationPendingPage = null;
let citationPendingHighlight = null;

    let selectedImageFile = null;
    let isListening = false;
    let recognition = null;

    let conversations = [];
    let activeConversationId = null;
    let conversationSaveQueue = Promise.resolve();
    let conversationStateReady = Promise.resolve();
    let conversationDocumentHash = null;

    // --------------------------------------------------------------------------
    // 3. Initialization Pipeline
    // --------------------------------------------------------------------------

    initTheme();
    initHighlightColor();
    initSpeechRecognition();
    initSupabaseAuth();
    const backendStatusReady = fetchBackendStatus();
    conversationStateReady = backendStatusReady.then(() => initConversationState());
    bindViewModeControls();
    bindPdfViewerControls();
    bindUploadEventHandlers();

    // --------------------------------------------------------------------------
    // 4. Theme & Highlight Color Engines
    // --------------------------------------------------------------------------

    function initTheme() {
        const savedTheme = localStorage.getItem('cwp_theme') || 'system';
        applyTheme(savedTheme);

        themeSelectRadios.forEach(radio => {
            radio.checked = radio.value === savedTheme;
            radio.addEventListener('change', (e) => {
                const selected = e.target.value;
                localStorage.setItem('cwp_theme', selected);
                applyTheme(selected);
            });
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }

    function initHighlightColor() {
        setHighlightColor(currentHighlightColor);

        colorSwatchBtns.forEach(btn => {
            const color = btn.getAttribute('data-color');
            if (color === currentHighlightColor) {
                btn.classList.add('active');
            }
            btn.addEventListener('click', () => {
                colorSwatchBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                setHighlightColor(color);
            });
        });

        if (customColorPicker) {
            customColorPicker.value = currentHighlightColor;
            customColorPicker.addEventListener('input', (e) => {
                colorSwatchBtns.forEach(b => b.classList.remove('active'));
                setHighlightColor(e.target.value);
            });
        }
    }

    function setHighlightColor(color) {
        currentHighlightColor = color;
        localStorage.setItem('cwp_highlight_color', color);
        if (highlightPreviewMark) {
            highlightPreviewMark.style.backgroundColor = color;
        }
    }

    // --------------------------------------------------------------------------
    // 5. Workspace View Mode Control (PDF / Chat / Split)
    // --------------------------------------------------------------------------

    function bindViewModeControls() {
        viewModeToggleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.getAttribute('data-mode');
                setWorkspaceViewMode(mode);
            });
        });
    }

    function setWorkspaceViewMode(mode) {
        currentViewMode = mode;
        if (!workspaceContainer) return;

        workspaceContainer.classList.remove('mode-split', 'mode-pdf', 'mode-chat');
        workspaceContainer.classList.add(`mode-${mode}`);

        viewModeToggleBtns.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
        });

        if (mode !== 'chat') {
            if (pdfNeedsLoad()) {
                loadPdfDocument('/api/pdf', currentDocument.filename);
            } else if (pdfDoc && !skipAutoRender) {
                setTimeout(() => renderPdfPage(pdfCurrentPage), 150);
            }
        }
    }

    // --------------------------------------------------------------------------
    // 6. PDF.js Engine & Renderer Implementation
    // --------------------------------------------------------------------------

    // State added for citation highlighting (kept next to the code that uses it).
    let activeHighlight = null;   // {page, specs}: highlight to (re)apply when this page is re-rendered
    let pdfLoadInFlight = null;   // {key, promise}: a second load of the same PDF joins the first

    function pdfNeedsLoad() {
        return !!(currentDocument && (!pdfDoc || pdfViewerTitle?.textContent !== currentDocument.filename));
    }

    function loadPdfDocument(pdfUrl, docFilename) {
        const key = `${pdfUrl}|${docFilename || ''}`;
        if (pdfLoadInFlight && pdfLoadInFlight.key === key) return pdfLoadInFlight.promise;
        const promise = loadPdfDocumentImpl(pdfUrl, docFilename).finally(() => {
            if (pdfLoadInFlight && pdfLoadInFlight.promise === promise) pdfLoadInFlight = null;
        });
        pdfLoadInFlight = { key, promise };
        return promise;
    }

    async function loadPdfDocumentImpl(pdfUrl, docFilename) {
        if (!window.pdfjsLib) {
            console.error('PDF.js library not available.');
            return;
        }

        try {
            if (pdfViewerTitle) pdfViewerTitle.textContent = docFilename || 'Loading PDF...';
            if (pdfEmptyState) pdfEmptyState.style.display = 'none';
            if (pdfCanvasWrapper) pdfCanvasWrapper.style.display = 'block';

            // Clean up previous PDF document proxy if one exists
            if (pdfDoc) {
                try {
                    await pdfDoc.destroy();
                } catch (cleanupErr) {
                    console.warn('PDF document destroy warning:', cleanupErr);
                }
                pdfDoc = null;
            }

            // Clear previous highlight overlay and canvas
            if (pdfTextHighlightOverlay) pdfTextHighlightOverlay.innerHTML = '';
            if (pdfCanvas) {
                const ctx = pdfCanvas.getContext('2d');
                if (ctx) ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
            }

            // Always add cache buster so browser/PDF.js never serves stale/previous PDF bytes
            const cacheBustedUrl = pdfUrl.includes('?')
                ? `${pdfUrl}&v=${encodeURIComponent(docFilename || '')}&_t=${Date.now()}`
                : `${pdfUrl}?v=${encodeURIComponent(docFilename || '')}&_t=${Date.now()}`;

            const loadingTask = pdfjsLib.getDocument({
                url: cacheBustedUrl,
                cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
                cMapPacked: true
            });
            pdfDoc = await loadingTask.promise;

            pdfTotalPages = pdfDoc.numPages;
            pdfCurrentPage = 1;
            if (pdfPageTotal) pdfPageTotal.textContent = pdfTotalPages;
            if (pdfPageNumInput) {
                pdfPageNumInput.max = pdfTotalPages;
                pdfPageNumInput.value = 1;
            }

            if (pdfViewerTitle) pdfViewerTitle.textContent = docFilename || 'Document.pdf';

            activeHighlight = null;
            // If a citation was clicked before the PDF finished loading, go straight to its page.
            if (citationPendingPage !== null) {
                const pPage = citationPendingPage, pHl = citationPendingHighlight;
                citationPendingPage = null;
                citationPendingHighlight = null;
                renderPdfPage(Math.min(Math.max(1, pPage), pdfTotalPages), pHl);
            } else {
                renderPdfPage(1);
            }
        } catch (err) {
            console.error('Error loading PDF in PDF.js:', err);
            citationPendingPage = null;
            citationPendingHighlight = null;
            if (pdfEmptyState) pdfEmptyState.style.display = 'flex';
            if (pdfCanvasWrapper) pdfCanvasWrapper.style.display = 'none';
            if (pdfViewerTitle) pdfViewerTitle.textContent = 'Failed to load PDF';
            showGlobalAlert('Could not render PDF document in viewer.', 'error');
        }
    }

    async function renderPdfPage(pageNum, highlightText = null) {
        if (!pdfDoc) return;
        // highlightText: null/undefined = "no change" (keep the highlight if this is the same page);
        // an array of {text, hint} (possibly empty) = explicit highlight for this page.
        if (highlightText !== null && highlightText !== undefined) {
            activeHighlight = { page: pageNum, specs: highlightText };
        } else if (!activeHighlight || activeHighlight.page !== pageNum) {
            activeHighlight = null;
        }
        if (pdfRendering) {
            pdfPendingPage = pageNum;
            pdfPendingHighlight = highlightText;
            return;
        }

        pdfRendering = true;
        pdfCurrentPage = pageNum;
        if (pdfPageNumInput) pdfPageNumInput.value = pageNum;

        let page;
        try {
            page = await pdfDoc.getPage(pageNum);
            const ctx = pdfCanvas.getContext('2d');

            const viewport = page.getViewport({ scale: pdfZoomScale });

            pdfCanvas.height = viewport.height;
            pdfCanvas.width = viewport.width;
            pdfCanvasWrapper.style.width = `${viewport.width}px`;
            // Let the wrapper follow the CSS-scaled canvas. A fixed viewport-pixel
            // height leaves the overlay taller than the visible canvas in split view.
            pdfCanvasWrapper.style.height = 'auto';

            const renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };

            await page.render(renderContext).promise;
            pdfRendering = false;

            if (pdfPendingPage !== null) {
                const pending = pdfPendingPage;
                const pendingHighlight = pdfPendingHighlight;
                pdfPendingPage = null;
                pdfPendingHighlight = null;
                renderPdfPage(pending, pendingHighlight);
                return;
            }

            if (pdfTextHighlightOverlay) pdfTextHighlightOverlay.innerHTML = '';

            if (activeHighlight && activeHighlight.page === pageNum && activeHighlight.specs && activeHighlight.specs.length) {
                await highlightTextOnCanvas(page, viewport, activeHighlight.specs);
            }
        } catch (err) {
            console.error('Error rendering PDF page:', err);
            pdfRendering = false;
        }
    }

    // Highlight verified citation evidence on the PDF canvas.
    // specs: [{text, hint}] from the server's validated citations. Matching is strict (highlight.js):
    // if the passage cannot be located unambiguously, nothing is drawn.
    async function highlightTextOnCanvas(page, viewport, specs) {
        try {
            if (!window.CWPHighlight) {
                console.warn('[CWP highlight] highlight.js not loaded; showing page without highlight.');
                return;
            }

            // The overlay has CSS width:100% height:100%, matching the wrapper's
            // displayed size.  The canvas backing-store is viewport.width ×
            // viewport.height but CSS `#pdfCanvas {width:100%}` scales it to
            // fit.  We express box positions as percentages of viewport
            // dimensions so they align with the scaled canvas in any container.
            const vpW = viewport.width;
            const vpH = viewport.height;

            const items = (await page.getTextContent()).items;
            let firstRect = null;
            (specs || []).forEach(spec => {
                const res = window.CWPHighlight.locate(items, spec.text, spec.hint);
                if (!res.ok) {
                    console.info('[CWP highlight] not drawn:', res.reason);
                    return;
                }
                res.segments.forEach(seg => {
                    const item = items[seg.itemIndex];
                    const len = Math.max(1, (item.str || '').length);
                    const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
                    const txFontH = Math.hypot(tx[2], tx[3]);
                    const fontHeight = (item.height > 0 ? item.height * viewport.scale : txFontH) || txFontH || Math.abs(tx[0]) || 12;
                    const itemWidth = item.width * viewport.scale;
                    const rectTop    = tx[5] - (fontHeight * 0.88);
                    const rectHeight = fontHeight * 1.15;
                    const rectLeft   = tx[4] + itemWidth * (seg.start / len);
                    const rectWidth  = itemWidth * ((seg.end - seg.start) / len);

                    // Convert viewport-pixel coords to percentages so boxes
                    // align with the CSS-scaled canvas regardless of container.
                    const box = document.createElement('div');
                    box.className = 'pdf-highlight-box';
                    box.style.left   = `${Math.max(0, (rectLeft   / vpW) * 100)}%`;
                    box.style.top    = `${Math.max(0, (rectTop    / vpH) * 100)}%`;
                    box.style.width  = `${Math.max(0.5, (rectWidth  / vpW) * 100)}%`;
                    box.style.height = `${Math.max(0.5, (rectHeight / vpH) * 100)}%`;
                    box.style.backgroundColor = currentHighlightColor;
                    pdfTextHighlightOverlay.appendChild(box);
                    if (!firstRect) firstRect = { top: rectTop };
                });
            });
            if (firstRect && pdfViewerStage) {
                const wrapperH = pdfCanvasWrapper ? pdfCanvasWrapper.clientHeight : vpH;
                const scrollTop = (firstRect.top / vpH) * wrapperH;
                pdfViewerStage.scrollTop = Math.max(0, scrollTop + 24 - 120);
            }
        } catch (e) {
            console.warn('Text highlighting overlay warning:', e);
        }
    }

    // Open the cited page; specs is [] when no verified evidence exists (page only, no highlight).
    function showCitation(page, specs) {
        const hl = Array.isArray(specs) ? specs : [];
        skipAutoRender = true;
        if (pdfNeedsLoad() || !pdfDoc) {
            // PDF not ready: remember the request; loadPdfDocument applies it when loading finishes.
            citationPendingPage = page;
            citationPendingHighlight = hl;
            setWorkspaceViewMode('split');
        } else {
            setWorkspaceViewMode('split');
            renderPdfPage(page, hl);
        }
        // Reset flag after the page has been rendered.
        setTimeout(() => { skipAutoRender = false; }, 500);
    }

    function bindPdfViewerControls() {
        btnPdfPrev?.addEventListener('click', () => {
            if (pdfCurrentPage > 1) {
                renderPdfPage(pdfCurrentPage - 1);
            }
        });

        btnPdfNext?.addEventListener('click', () => {
            if (pdfCurrentPage < pdfTotalPages) {
                renderPdfPage(pdfCurrentPage + 1);
            }
        });

        pdfPageNumInput?.addEventListener('change', (e) => {
            const num = parseInt(e.target.value, 10);
            if (num >= 1 && num <= pdfTotalPages) {
                renderPdfPage(num);
            }
        });

        btnPdfZoomIn?.addEventListener('click', () => {
            if (pdfZoomScale < 2.5) {
                pdfZoomScale += 0.2;
                if (pdfZoomLabel) pdfZoomLabel.textContent = `${Math.round(pdfZoomScale * 100)}%`;
                renderPdfPage(pdfCurrentPage);
            }
        });

        btnPdfZoomOut?.addEventListener('click', () => {
            if (pdfZoomScale > 0.6) {
                pdfZoomScale -= 0.2;
                if (pdfZoomLabel) pdfZoomLabel.textContent = `${Math.round(pdfZoomScale * 100)}%`;
                renderPdfPage(pdfCurrentPage);
            }
        });

        btnPdfFitWidth?.addEventListener('click', () => {
            pdfZoomScale = 1.0;
            if (pdfZoomLabel) pdfZoomLabel.textContent = '100%';
            renderPdfPage(pdfCurrentPage);
        });
    }

    function resetPdfViewerState() {
        pdfDoc = null;
        activeHighlight = null;
        citationPendingPage = null;
        citationPendingHighlight = null;
        pdfCurrentPage = 1;
        pdfTotalPages = 1;
        pdfZoomScale = 1.0;
        if (pdfEmptyState) pdfEmptyState.style.display = 'flex';
        if (pdfCanvasWrapper) pdfCanvasWrapper.style.display = 'none';
        if (pdfViewerTitle) pdfViewerTitle.textContent = 'No Document Loaded';
        if (pdfTextHighlightOverlay) pdfTextHighlightOverlay.innerHTML = '';
    }

    // --------------------------------------------------------------------------
    // 7. Supabase Authentication Setup & Integration
    // --------------------------------------------------------------------------

    // Helper functions for local session management
    function getLocalSession() {
        try {
            const stored = localStorage.getItem('cwp_local_session');
            if (stored) return JSON.parse(stored);
        } catch (e) {
            console.error('Error reading local session:', e);
        }
        return null;
    }

    function setLocalSession(email, fullName) {
        const session = {
            user: {
                id: 'local_' + Date.now(),
                email: email || 'guest@cwp.local',
                user_metadata: {
                    full_name: fullName || (email ? email.split('@')[0] : 'Guest User')
                }
            }
        };
        try {
            localStorage.setItem('cwp_local_session', JSON.stringify(session));
        } catch (e) {
            console.error('Error saving local session:', e);
        }
        return session;
    }

    function clearLocalSession() {
        try {
            localStorage.removeItem('cwp_local_session');
        } catch (e) { }
    }

    async function initSupabaseAuth() {
        let config = null;
        try {
            const res = await fetch('/api/config');
            config = await res.json();
        } catch (err) {
            console.warn('Could not fetch /api/config:', err);
        }

        const isConfigured = config && config.supabase_configured;

        if (isConfigured && window.supabase) {
            try {
                supabaseClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key);
                const { data: { session }, error } = await supabaseClient.auth.getSession();

                if (!error && session) {
                    handleSessionState(session);
                } else {
                    checkLocalOrShowAuth();
                }

                supabaseClient.auth.onAuthStateChange((event, session) => {
                    if (session) {
                        handleSessionState(session);
                    } else if (event === 'SIGNED_OUT') {
                        clearLocalSession();
                        handleSessionState(null);
                    }
                });
            } catch (err) {
                console.warn('Supabase initialization failed, falling back to local auth:', err);
                supabaseClient = null;
                checkLocalOrShowAuth();
            }
        } else {
            supabaseClient = null;
            checkLocalOrShowAuth();
        }

        bindAuthFormEvents();
    }

    function checkLocalOrShowAuth() {
        const localSession = getLocalSession();
        if (localSession) {
            handleSessionState(localSession);
        } else {
            showAuthModal();
        }
    }

    function handleSessionState(session) {
        currentSession = session;
        if (session && session.user) {
            hideAuthModal();
            updateUserUI(session.user);
        } else {
            showAuthModal();
            updateUserUI(null);
        }
    }

    function bindAuthFormEvents() {
        document.querySelectorAll('.btn-toggle-pwd').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.getAttribute('data-target');
                const pwdInput = document.getElementById(targetId);
                if (pwdInput) {
                    const isPwd = pwdInput.type === 'password';
                    pwdInput.type = isPwd ? 'text' : 'password';
                }
            });
        });

        btnGoSignUp?.addEventListener('click', () => showAuthForm('signUp'));
        btnGoSignIn?.addEventListener('click', () => showAuthForm('signIn'));
        btnGoForgot?.addEventListener('click', () => showAuthForm('forgot'));
        btnGoSignInFromForgot?.addEventListener('click', () => showAuthForm('signIn'));

        const btnGuestSignIn = document.getElementById('btnGuestSignIn');
        btnGuestSignIn?.addEventListener('click', () => {
            const guestSess = setLocalSession('guest@cwp.local', 'Guest User');
            hideAuthAlert();
            handleSessionState(guestSess);
            showGlobalAlert('Welcome to CWP Intelligence Workspace! Signed in as Guest.', 'success');
        });

        signInForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('signInEmail').value.trim();
            const password = document.getElementById('signInPassword').value.trim();

            if (!email || !password) {
                showAuthAlert('Please fill in both email and password.');
                return;
            }

            if (btnSignInSubmit) btnSignInSubmit.disabled = true;
            showAuthAlert('Signing in...', 'info');

            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient.auth.signInWithPassword({
                        email: email,
                        password: password
                    });

                    if (error) {
                        const errMsg = (error.message || '').toLowerCase();
                        if (errMsg.includes('load failed') || errMsg.includes('fetch') || errMsg.includes('network') || error.status === 0) {
                            console.warn('Supabase request failed due to network/domain issue. Logging in using local mode.');
                            const localSess = setLocalSession(email, email.split('@')[0]);
                            hideAuthAlert();
                            handleSessionState(localSess);
                            showGlobalAlert(`Welcome back, ${localSess.user.user_metadata.full_name}! (Local Mode)`, 'success');
                        } else {
                            showAuthAlert(error.message || 'Invalid email or password.', 'error');
                        }
                    } else if (data && data.user) {
                        hideAuthAlert();
                        handleSessionState(data.session);
                        showGlobalAlert(`Welcome back, ${data.user.user_metadata?.full_name || data.user.email}!`, 'success');
                    }
                } catch (err) {
                    console.warn('Caught exception during sign in. Using local mode.', err);
                    const localSess = setLocalSession(email, email.split('@')[0]);
                    hideAuthAlert();
                    handleSessionState(localSess);
                    showGlobalAlert(`Welcome back, ${localSess.user.user_metadata.full_name}! (Local Mode)`, 'success');
                } finally {
                    if (btnSignInSubmit) btnSignInSubmit.disabled = false;
                }
            } else {
                const localSess = setLocalSession(email, email.split('@')[0]);
                hideAuthAlert();
                handleSessionState(localSess);
                showGlobalAlert(`Welcome back, ${localSess.user.user_metadata.full_name}!`, 'success');
                if (btnSignInSubmit) btnSignInSubmit.disabled = false;
            }
        });

        signUpForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('signUpName').value.trim();
            const email = document.getElementById('signUpEmail').value.trim();
            const password = document.getElementById('signUpPassword').value;
            const confirmPassword = document.getElementById('signUpConfirmPassword').value;

            if (!name || !email || !password) {
                showAuthAlert('Please complete all required fields.');
                return;
            }

            if (password !== confirmPassword) {
                showAuthAlert('Passwords do not match. Please check and try again.');
                return;
            }

            if (password.length < 6) {
                showAuthAlert('Password must be at least 6 characters long.');
                return;
            }

            if (btnSignUpSubmit) btnSignUpSubmit.disabled = true;
            showAuthAlert('Creating account...', 'info');

            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient.auth.signUp({
                        email: email,
                        password: password,
                        options: {
                            data: { full_name: name }
                        }
                    });

                    if (error) {
                        const errMsg = (error.message || '').toLowerCase();
                        if (errMsg.includes('load failed') || errMsg.includes('fetch') || errMsg.includes('network') || error.status === 0) {
                            console.warn('Supabase sign up failed due to network issue. Creating local account.');
                            const localSess = setLocalSession(email, name);
                            hideAuthAlert();
                            handleSessionState(localSess);
                            showGlobalAlert(`Account created successfully! Welcome, ${name}. (Local Mode)`, 'success');
                        } else {
                            showAuthAlert(error.message || 'Registration failed.', 'error');
                        }
                    } else if (data.user && !data.session) {
                        showAuthAlert('Account created! Please check your email to confirm registration.', 'success');
                    } else {
                        hideAuthAlert();
                        handleSessionState(data.session || setLocalSession(email, name));
                        showGlobalAlert(`Account created successfully! Welcome, ${name}.`, 'success');
                    }
                } catch (err) {
                    const localSess = setLocalSession(email, name);
                    hideAuthAlert();
                    handleSessionState(localSess);
                    showGlobalAlert(`Account created successfully! Welcome, ${name}. (Local Mode)`, 'success');
                } finally {
                    if (btnSignUpSubmit) btnSignUpSubmit.disabled = false;
                }
            } else {
                const localSess = setLocalSession(email, name);
                hideAuthAlert();
                handleSessionState(localSess);
                showGlobalAlert(`Account created successfully! Welcome, ${name}.`, 'success');
                if (btnSignUpSubmit) btnSignUpSubmit.disabled = false;
            }
        });

        forgotPasswordForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('forgotEmail').value.trim();

            if (!email) {
                showAuthAlert('Please enter your email address.');
                return;
            }

            if (btnForgotSubmit) btnForgotSubmit.disabled = true;
            showAuthAlert('Sending password reset instructions...', 'info');

            if (supabaseClient) {
                try {
                    const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
                        redirectTo: window.location.origin
                    });

                    if (error) {
                        showAuthAlert(error.message || 'Could not send reset email.', 'error');
                    } else {
                        showAuthAlert(`Password reset link sent to ${email}.`, 'success');
                    }
                } catch (err) {
                    showAuthAlert('Password reset request failed.', 'error');
                } finally {
                    if (btnForgotSubmit) btnForgotSubmit.disabled = false;
                }
            } else {
                showAuthAlert(`Password reset simulated for ${email}. You can sign in directly.`, 'success');
                if (btnForgotSubmit) btnForgotSubmit.disabled = false;
            }
        });

        btnUserMenu?.addEventListener('click', (e) => {
            e.stopPropagation();
            if (userMenuDropdown) {
                const isVis = userMenuDropdown.style.display === 'block';
                userMenuDropdown.style.display = isVis ? 'none' : 'block';
            }
        });

        document.addEventListener('click', () => {
            if (userMenuDropdown) userMenuDropdown.style.display = 'none';
        });

        btnDropdownSettings?.addEventListener('click', () => showSettingsModal());
        btnSidebarSettings?.addEventListener('click', () => showSettingsModal());
        btnDropdownSignOut?.addEventListener('click', signOutUser);
        btnSettingsSignOut?.addEventListener('click', signOutUser);

        btnOpenChangePassword?.addEventListener('click', () => showChangePasswordModal());
        btnCloseChangePwd?.addEventListener('click', () => hideChangePasswordModal());

        verifyCurrPasswordForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const currPwd = document.getElementById('currPasswordInput').value;

            if (!currPwd) {
                showChangePwdAlert('Please enter your current password.');
                return;
            }

            if (!currentSession || !currentSession.user) {
                showChangePwdAlert('User session expired. Please sign in again.');
                return;
            }

            showChangePwdAlert('Verifying current password...', 'info');

            try {
                const { error } = await supabaseClient.auth.signInWithPassword({
                    email: currentSession.user.email,
                    password: currPwd
                });

                if (error) {
                    showChangePwdAlert('Current password verification failed. Please try again.', 'error');
                } else {
                    hideChangePwdAlert();
                    verifyCurrPasswordForm.style.display = 'none';
                    setNewPasswordForm.style.display = 'flex';
                    if (changePasswordSubtitle) changePasswordSubtitle.textContent = 'Enter and confirm your new password';
                }
            } catch (err) {
                showChangePwdAlert('Error verifying password.', 'error');
            }
        });

        btnForgotFromChangePassword?.addEventListener('click', async () => {
            if (!currentSession || !currentSession.user) return;
            showChangePwdAlert('Sending reset instructions...', 'info');

            try {
                const { error } = await supabaseClient.auth.resetPasswordForEmail(currentSession.user.email, {
                    redirectTo: window.location.origin
                });

                if (error) {
                    showChangePwdAlert(error.message || 'Could not send reset link.', 'error');
                } else {
                    showChangePwdAlert(`Password reset link sent to ${currentSession.user.email}.`, 'success');
                }
            } catch (err) {
                showChangePwdAlert('Error requesting password reset.', 'error');
            }
        });

        setNewPasswordForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const newPwd = document.getElementById('newPasswordInput').value;
            const confirmPwd = document.getElementById('confirmNewPasswordInput').value;

            if (newPwd !== confirmPwd) {
                showChangePwdAlert('Passwords do not match.', 'error');
                return;
            }

            if (newPwd.length < 6) {
                showChangePwdAlert('Password must be at least 6 characters long.', 'error');
                return;
            }

            showChangePwdAlert('Updating password...', 'info');

            try {
                const { error } = await supabaseClient.auth.updateUser({ password: newPwd });

                if (error) {
                    showChangePwdAlert(error.message || 'Failed to update password.', 'error');
                } else {
                    hideChangePasswordModal();
                    showGlobalAlert('Password updated successfully.', 'success');
                }
            } catch (err) {
                showChangePwdAlert('Error updating password.', 'error');
            }
        });

        btnToggleSidebarMobile?.addEventListener('click', () => {
            if (sidebarPanel) {
                sidebarPanel.classList.toggle('open');
            }
        });
    }

    function showAuthForm(formType) {
        hideAuthAlert();
        if (signInForm) signInForm.style.display = formType === 'signIn' ? 'flex' : 'none';
        if (signUpForm) signUpForm.style.display = formType === 'signUp' ? 'flex' : 'none';
        if (forgotPasswordForm) forgotPasswordForm.style.display = formType === 'forgot' ? 'flex' : 'none';

        if (authTitle && authSubtitle) {
            if (formType === 'signIn') {
                authTitle.textContent = 'Sign In';
                authSubtitle.textContent = 'Access your PDF research workspace and chat history';
            } else if (formType === 'signUp') {
                authTitle.textContent = 'Create Account';
                authSubtitle.textContent = 'Start analyzing documents with grounded AI';
            } else if (formType === 'forgot') {
                authTitle.textContent = 'Reset Password';
                authSubtitle.textContent = 'Enter your email to receive password recovery instructions';
            }
        }
    }

    function showAuthAlert(msg, type = 'error') {
        if (authAlert) {
            authAlert.textContent = msg;
            authAlert.className = `auth-alert ${type}`;
            authAlert.style.display = 'block';
        }
    }

    function hideAuthAlert() {
        if (authAlert) authAlert.style.display = 'none';
    }

    function showAuthModal() {
        if (authModal) authModal.style.display = 'flex';
        showAuthForm('signIn');
    }

    function hideAuthModal() {
        if (authModal) authModal.style.display = 'none';
    }

    function showChangePasswordModal() {
        if (changePasswordModal) changePasswordModal.style.display = 'flex';
        if (verifyCurrPasswordForm) verifyCurrPasswordForm.style.display = 'flex';
        if (setNewPasswordForm) setNewPasswordForm.style.display = 'none';
        if (changePasswordTitle) changePasswordTitle.textContent = 'Change Password';
        if (changePasswordSubtitle) changePasswordSubtitle.textContent = 'Verify your current password to continue';
        hideChangePwdAlert();
    }

    function hideChangePasswordModal() {
        if (changePasswordModal) changePasswordModal.style.display = 'none';
    }

    function showChangePwdAlert(msg, type = 'error') {
        if (changePwdAlert) {
            changePwdAlert.textContent = msg;
            changePwdAlert.className = `auth-alert ${type}`;
            changePwdAlert.style.display = 'block';
        }
    }

    function hideChangePwdAlert() {
        if (changePwdAlert) changePwdAlert.style.display = 'none';
    }

    function updateUserUI(user) {
        if (user) {
            const name = user.user_metadata?.full_name || user.email.split('@')[0];
            const initial = name.charAt(0).toUpperCase();

            if (userAvatarText) userAvatarText.textContent = initial;
            if (dropdownUserName) dropdownUserName.textContent = name;
            if (dropdownUserEmail) dropdownUserEmail.textContent = user.email;

            if (settingsAvatar) settingsAvatar.textContent = initial;
            if (settingsProfileName) settingsProfileName.textContent = name;
            if (settingsProfileEmail) settingsProfileEmail.textContent = user.email;
        } else {
            if (userAvatarText) userAvatarText.textContent = 'U';
            if (dropdownUserName) dropdownUserName.textContent = 'User';
            if (dropdownUserEmail) dropdownUserEmail.textContent = 'user@example.com';

            if (settingsAvatar) settingsAvatar.textContent = 'U';
            if (settingsProfileName) settingsProfileName.textContent = 'Authenticated User';
            if (settingsProfileEmail) settingsProfileEmail.textContent = 'user@example.com';
        }
    }

    async function signOutUser() {
        await conversationSaveQueue.catch(() => {});
        try {
            await fetch('/api/session/logout', { method: 'POST' });
        } catch (e) {
            console.warn('Server session sign-out failed.');
        }
        if (supabaseClient) {
            try {
                await supabaseClient.auth.signOut();
            } catch (e) {
                console.warn('Supabase sign out warning:', e);
            }
        }
        clearLocalSession();
        currentSession = null;
        documentRevision += 1;
        conversations = [];
        activeConversationId = null;
        currentDocument = null;
        conversationDocumentHash = null;
        if (chatMessages) chatMessages.innerHTML = '';
        updateUserUI(null);
        showGlobalAlert('Signed out successfully.', 'info');
        showAuthModal();
    }

    // --------------------------------------------------------------------------
    // 8. Backend Status & Active Document Control
    // --------------------------------------------------------------------------

    async function fetchBackendStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            if (data.status === 'ready' && data.document) {
                if (systemStatusEl) systemStatusEl.className = 'status-indicator ready';
                if (statusTextEl) statusTextEl.textContent = 'Document Ready';
                updateDocumentUI(data.document);
                loadPdfDocument('/api/pdf', data.document.filename);
            } else {
                if (systemStatusEl) systemStatusEl.className = 'status-indicator';
                if (statusTextEl) statusTextEl.textContent = 'No Document Loaded';
                showDocumentEmptyState();
                resetPdfViewerState();
            }
        } catch (err) {
            console.error('Failed to fetch status:', err);
            if (systemStatusEl) systemStatusEl.className = 'status-indicator error';
            if (statusTextEl) statusTextEl.textContent = 'Disconnected';
            showGlobalAlert('Could not connect to CWP backend server.', 'error');
            showDocumentEmptyState();
            resetPdfViewerState();
        }
    }

    function updateDocumentUI(doc) {
        currentDocument = doc;
        conversationDocumentHash = doc.hash || null;

        if (headerDocIndicator) headerDocIndicator.classList.add('active');
        if (headerDocName) headerDocName.textContent = doc.filename;

        if (dropZone) dropZone.style.display = 'none';
        if (pdfLoadedZone) pdfLoadedZone.style.display = 'flex';
        if (loadedDocFilename) loadedDocFilename.textContent = doc.filename;
        if (btnRemovePdf) btnRemovePdf.style.display = 'inline-block';

        if (welcomeTitle) welcomeTitle.textContent = 'Ask structural & conceptual questions grounded in your PDF';
        if (welcomeSubtitle) welcomeSubtitle.textContent = 'Query exact question numbers, process sequences, topic lists, or conceptual explanations.';
        if (welcomeSuggestions) welcomeSuggestions.style.display = 'block';

        updateSettingsDocUI();
        renderSuggestedQuestions(doc.suggested_questions);
    }

    function showDocumentEmptyState() {
        currentDocument = null;
        conversationDocumentHash = null;

        if (headerDocIndicator) headerDocIndicator.classList.remove('active');
        if (headerDocName) headerDocName.textContent = 'No Active PDF';

        if (dropZone) dropZone.style.display = 'block';
        if (pdfLoadedZone) pdfLoadedZone.style.display = 'none';
        if (btnRemovePdf) btnRemovePdf.style.display = 'none';

        if (welcomeTitle) welcomeTitle.textContent = 'Upload a PDF to start asking questions';
        if (welcomeSubtitle) welcomeSubtitle.textContent = 'Upload your document to explore structural & conceptual Q&A grounded in your PDF.';
        if (welcomeSuggestions) welcomeSuggestions.style.display = 'none';

        updateSettingsDocUI();
        resetPdfViewerState();
    }

    function updateSettingsDocUI() {
        if (currentDocument) {
            if (settingsDocName) settingsDocName.textContent = currentDocument.filename;
            if (settingsDocStatus) {
                settingsDocStatus.textContent = 'Ready';
                settingsDocStatus.className = 'status-pill success';
            }
            if (btnSettingsRemove) btnSettingsRemove.style.display = 'inline-flex';
        } else {
            if (settingsDocName) settingsDocName.textContent = 'No document loaded';
            if (settingsDocStatus) {
                settingsDocStatus.textContent = 'No PDF';
                settingsDocStatus.className = 'status-pill warning';
            }
            if (btnSettingsRemove) btnSettingsRemove.style.display = 'none';
        }
    }

    function renderSuggestedQuestions(questions) {
        if (!suggestionsList) return;
        suggestionsList.innerHTML = '';

        if (!currentDocument) {
            if (welcomeSuggestions) welcomeSuggestions.style.display = 'none';
            return;
        }

        const list = (questions && questions.length > 0) ? questions : [
            "What is the 3rd question under the 2-mark questions?",
            "What are the six steps of HRP?",
            "What are the major topics covered in this PDF?"
        ];

        list.forEach(q => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'suggestion-chip';
            chip.setAttribute('data-question', q);
            chip.textContent = q;
            chip.addEventListener('click', () => {
                submitUserQuestion(q, null, true);
            });
            suggestionsList.appendChild(chip);
        });

        if (welcomeSuggestions) welcomeSuggestions.style.display = 'block';
    }

    // --------------------------------------------------------------------------
    // 9. PDF Upload & File Picker Fixes
    // --------------------------------------------------------------------------

    function bindUploadEventHandlers() {
        dropZone?.addEventListener('click', () => {
            if (pdfFileInput) {
                pdfFileInput.value = '';
                pdfFileInput.click();
            }
        });

        btnSettingsUpload?.addEventListener('click', () => {
            if (pdfFileInput) {
                pdfFileInput.value = '';
                pdfFileInput.click();
            }
        });

        dropZone?.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

        dropZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                handlePdfFileUpload(files[0]);
            }
        });

        pdfFileInput?.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
                handlePdfFileUpload(files[0]);
                pdfFileInput.value = '';
            }
        });

        btnRemovePdf?.addEventListener('click', () => showRemoveConfirmModal());
        btnSettingsRemove?.addEventListener('click', () => showRemoveConfirmModal());

        btnCancelRemoveDoc?.addEventListener('click', () => {
            if (confirmRemoveModal) confirmRemoveModal.style.display = 'none';
        });

        btnConfirmRemoveDoc?.addEventListener('click', async () => {
            if (confirmRemoveModal) confirmRemoveModal.style.display = 'none';

            try {
                const res = await fetch('/api/document', { method: 'DELETE' });
                if (res.ok) {
                    documentRevision += 1;
                    conversations = [];
                    activeConversationId = null;
                    showDocumentEmptyState();
                    createNewConversation();
                    showGlobalAlert('Active document removed from workspace.', 'info');
                } else {
                    const data = await res.json();
                    showGlobalAlert(data.detail || 'Could not remove document.', 'error');
                }
            } catch (err) {
                showGlobalAlert('Error requesting document removal.', 'error');
            }
        });
    }

    async function handlePdfFileUpload(file) {
        await conversationStateReady;
        await conversationSaveQueue.catch(() => {});
        if (pdfUploadInProgress) {
            showGlobalAlert('A PDF upload is already being processed.', 'warning');
            return;
        }
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showGlobalAlert('Only PDF files are supported.', 'warning');
            return;
        }

        pdfUploadInProgress = true;
        const formData = new FormData();
        formData.append('file', file);

        showGlobalAlert(`Uploading and indexing '${file.name}'...`, 'info');

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (res.ok && data.success) {
                documentRevision += 1;
                conversations = [];
                activeConversationId = null;
                createNewConversation();
                updateDocumentUI(data.document);
                await loadPdfDocument('/api/pdf', data.document.filename);
                showGlobalAlert(`Successfully loaded '${file.name}'.`, 'success');
            } else {
                showGlobalAlert(data.detail || 'Failed to upload PDF.', 'error');
            }
        } catch (err) {
            console.error('PDF upload error:', err);
            showGlobalAlert('Error uploading PDF file to server.', 'error');
        } finally {
            pdfUploadInProgress = false;
        }
    }

    function showRemoveConfirmModal() {
        if (confirmDocName) confirmDocName.textContent = currentDocument ? currentDocument.filename : 'active PDF';
        if (confirmRemoveModal) confirmRemoveModal.style.display = 'flex';
    }

    // --------------------------------------------------------------------------
    // 10. Chat Message Submission & Grounded RAG Response Pipeline
    // --------------------------------------------------------------------------

    let isGenerating = false;

    function setGeneratingState(generating) {
        isGenerating = generating;
        if (btnSubmit) btnSubmit.disabled = generating;
        if (questionInput) questionInput.disabled = generating;
        document.querySelectorAll('.btn-msg-action').forEach(btn => {
            btn.disabled = generating;
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async function submitUserQuestion(questionText, imageFile = null, appendToChat = true) {
        await conversationStateReady;
        const currentQ = (questionText || '').trim();
        const currentImg = imageFile;

        if (!currentQ && !currentImg) {
            return;
        }

        if (isGenerating) {
            return;
        }

        // Verify active PDF document
        if (!currentDocument) {
            showGlobalAlert('No active PDF loaded. Please upload a PDF document before asking questions.', 'warning');
            appendAssistantErrorMessage('No active PDF loaded. Please upload a PDF before asking questions.', currentQ);
            return;
        }
        const requestDocumentRevision = documentRevision;
        const requestConversationId = activeConversationId;

        if (currentQ) {
            autoTitleActiveConversation(currentQ);
        }

        if (appendToChat) {
            appendUserMessage(currentQ, currentImg);
            recordMessageInActiveConversation('user', currentQ);
        }

        if (questionInput) {
            questionInput.value = '';
            questionInput.style.height = 'auto';
        }
        clearAttachmentPreview();

        setGeneratingState(true);
        const loadingBubble = appendAssistantLoadingMessage();

        try {
            let res;
            if (currentImg) {
                const formData = new FormData();
                formData.append('file', currentImg);
                if (currentQ) formData.append('question', currentQ);

                res = await fetch('/api/chat/image', {
                    method: 'POST',
                    body: formData
                });
            } else {
                res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: currentQ })
                });
            }

            let data = null;
            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                data = await res.json();
            } else {
                const text = await res.text();
                try {
                    data = JSON.parse(text);
                } catch {
                    data = { detail: text };
                }
            }

            loadingBubble.remove();
            if (requestDocumentRevision !== documentRevision || requestConversationId !== activeConversationId) {
                return;
            }

            if (res.ok && data) {
                if (data.answer) {
                    const cites = stampCitations(data.citations);
                    appendAssistantMessage(data.answer, data.sources, data.retrieved_chunks, currentQ, null, cites);
                    recordMessageInActiveConversation('assistant', data.answer, data.sources, data.retrieved_chunks, currentQ, cites);
                } else if (data.requires_fallback) {
                    const fallbackMsg = data.fallback_prompt || data.message || 'The PDF context does not contain enough information to answer this question.';
                    appendAssistantFallbackMessage(currentQ, fallbackMsg);
                    recordMessageInActiveConversation('assistant', fallbackMsg, [], [], currentQ, []);
                } else {
                    const fallbackMsg = data.message || 'The PDF context does not contain enough information to answer this question.';
                    appendAssistantNoAnswerMessage(currentQ, fallbackMsg);
                    recordMessageInActiveConversation('assistant', fallbackMsg, [], [], currentQ);
                }
            } else {
                let errorMsg = 'Failed to generate answer.';
                if (res.status === 400) {
                    errorMsg = (data && data.detail) || 'No active PDF loaded or question is empty. Please upload a PDF.';
                } else if (res.status === 429) {
                    errorMsg = (data && data.detail) || 'AI model rate limit reached. Please wait a moment and try again.';
                } else if (res.status === 503) {
                    errorMsg = (data && data.detail) || 'AI model is currently experiencing high demand. Please try again in a few moments.';
                } else if (res.status >= 500) {
                    errorMsg = (data && data.detail) || 'Server error occurred while processing the answer. Please try again.';
                } else if (data && (data.detail || data.message)) {
                    errorMsg = data.detail || data.message;
                }
                appendAssistantErrorMessage(errorMsg, currentQ);
                recordMessageInActiveConversation('assistant', `Error: ${errorMsg}`, [], [], currentQ);
            }
        } catch (err) {
            console.error('Chat error:', err);
            loadingBubble.remove();
            if (err instanceof TypeError || !navigator.onLine) {
                appendAssistantErrorMessage('Network connection error: Unable to reach backend server. Please verify the server is running on port 8000 and check your connection.', currentQ);
            } else {
                appendAssistantErrorMessage(`Error: ${err.message || 'An unexpected error occurred.'}`, currentQ);
            }
        } finally {
            setGeneratingState(false);
        }
    }

    chatForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const questionText = questionInput.value.trim();
        const imgFile = selectedImageFile;
        submitUserQuestion(questionText, imgFile, true);
    });

    function appendUserMessage(text, imgFile, msgIndex = null) {
        if (welcomeCard) welcomeCard.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper user';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        if (imgFile) {
            const imgEl = document.createElement('img');
            imgEl.src = URL.createObjectURL(imgFile);
            imgEl.className = 'chat-attached-img';
            imgEl.style.maxWidth = '200px';
            imgEl.style.borderRadius = '8px';
            imgEl.style.marginBottom = '8px';
            imgEl.style.display = 'block';
            bubble.appendChild(imgEl);
        }

        const textSpan = document.createElement('span');
        textSpan.className = 'user-text-content';
        if (text) {
            textSpan.textContent = text;
        }
        bubble.appendChild(textSpan);
        wrapper.appendChild(bubble);

        // ChatGPT-like User Message Toolbar: Copy, Edit, Retry/Resend
        if (text) {
            const toolbar = document.createElement('div');
            toolbar.className = 'msg-toolbar';

            // 1. Copy Prompt
            const copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.className = 'btn-msg-action btn-copy-prompt';
            copyBtn.setAttribute('aria-label', 'Copy prompt');
            copyBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span class="btn-popout-label">Copy</span>
            `;
            copyBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                try {
                    await navigator.clipboard.writeText(textSpan.textContent || text);
                    copyBtn.classList.add('copied');
                    copyBtn.innerHTML = `
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span class="btn-popout-label">Copied!</span>
                    `;
                    setTimeout(() => {
                        copyBtn.classList.remove('copied');
                        copyBtn.innerHTML = `
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            <span class="btn-popout-label">Copy</span>
                        `;
                    }, 2000);
                } catch {
                    showGlobalAlert('Unable to copy prompt to clipboard', 'warning');
                }
            });

            // 2. Edit Prompt
            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'btn-msg-action btn-edit-prompt';
            editBtn.setAttribute('aria-label', 'Edit prompt');
            editBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                <span class="btn-popout-label">Edit</span>
            `;
            editBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (isGenerating) return;

                textSpan.style.display = 'none';
                toolbar.style.display = 'none';

                let editBox = bubble.querySelector('.inline-edit-box');
                if (!editBox) {
                    editBox = document.createElement('div');
                    editBox.className = 'inline-edit-box';
                    editBox.innerHTML = `
                        <textarea class="inline-edit-textarea"></textarea>
                        <div class="inline-edit-actions">
                            <button type="button" class="btn-edit-cancel">Cancel</button>
                            <button type="button" class="btn-edit-save">Save & Submit</button>
                        </div>
                    `;
                    bubble.appendChild(editBox);
                } else {
                    editBox.style.display = 'flex';
                }

                const textarea = editBox.querySelector('.inline-edit-textarea');
                textarea.value = textSpan.textContent;
                textarea.focus();

                const cancelBtn = editBox.querySelector('.btn-edit-cancel');
                const saveBtn = editBox.querySelector('.btn-edit-save');

                cancelBtn.onclick = () => {
                    editBox.style.display = 'none';
                    textSpan.style.display = 'inline';
                    toolbar.style.display = 'flex';
                };

                saveBtn.onclick = async () => {
                    const updatedText = textarea.value.trim();
                    if (!updatedText) return;

                    editBox.style.display = 'none';
                    const originalText = textSpan.textContent;
                    textSpan.textContent = updatedText;
                    textSpan.style.display = 'inline';
                    toolbar.style.display = 'flex';

                    // Update prompt in active conversation history
                    const activeConv = conversations.find(c => c.id === activeConversationId);
                    if (activeConv && activeConv.messages) {
                        let targetIdx = msgIndex;
                        if (targetIdx === null || targetIdx === undefined) {
                            targetIdx = activeConv.messages.findIndex(m => m.sender === 'user' && m.text === originalText);
                        }
                        if (targetIdx !== -1 && targetIdx < activeConv.messages.length) {
                            activeConv.messages[targetIdx].text = updatedText;
                            // Avoid leaving misleading old response: remove subsequent assistant response
                            if (activeConv.messages[targetIdx + 1] && activeConv.messages[targetIdx + 1].sender === 'assistant') {
                                activeConv.messages.splice(targetIdx + 1, 1);
                            }
                            saveConversations();
                        }
                    }

                    // Remove subsequent assistant response in DOM
                    const nextEl = wrapper.nextElementSibling;
                    if (nextEl && nextEl.classList.contains('assistant')) {
                        nextEl.remove();
                    }

                    // Regenerate response for the updated prompt
                    await submitUserQuestion(updatedText, null, false);
                };
            });

            // 3. Retry / Resend Prompt
            const retryBtn = document.createElement('button');
            retryBtn.type = 'button';
            retryBtn.className = 'btn-msg-action btn-resend-prompt';
            retryBtn.setAttribute('aria-label', 'Resend prompt');
            retryBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                <span class="btn-popout-label">Resend</span>
            `;
            retryBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (isGenerating) return;

                const currentPrompt = textSpan.textContent || text;
                const activeConv = conversations.find(c => c.id === activeConversationId);
                if (activeConv && activeConv.messages) {
                    let targetIdx = msgIndex;
                    if (targetIdx === null || targetIdx === undefined) {
                        targetIdx = activeConv.messages.findIndex(m => m.sender === 'user' && m.text === currentPrompt);
                    }
                    if (targetIdx !== -1 && activeConv.messages[targetIdx + 1] && activeConv.messages[targetIdx + 1].sender === 'assistant') {
                        activeConv.messages.splice(targetIdx + 1, 1);
                        saveConversations();
                    }
                }
                const nextEl = wrapper.nextElementSibling;
                if (nextEl && nextEl.classList.contains('assistant')) {
                    nextEl.remove();
                }

                await submitUserQuestion(currentPrompt, null, false);
            });

            toolbar.appendChild(copyBtn);
            toolbar.appendChild(editBtn);
            toolbar.appendChild(retryBtn);
            wrapper.appendChild(toolbar);

            // Touch accessibility toggle
            wrapper.addEventListener('click', (e) => {
                if (e.target.closest('.btn-msg-action') || e.target.closest('.inline-edit-box')) return;
                wrapper.classList.toggle('touch-show');
            });
        }

        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
        return wrapper;
    }

    function appendAssistantLoadingMessage() {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble loading';
        bubble.innerHTML = '<span class="loading-dots">Searching PDF and generating grounded answer...</span>';

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
        return wrapper;
    }

    function appendAssistantMessage(answerText, sources, chunks, correspondingQuestion = null, msgIndex = null, citations = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const textContainer = document.createElement('div');
        textContainer.className = 'assistant-text-content';
        textContainer.innerHTML = formatMarkdownText(answerText);
        bubble.appendChild(textContainer);

        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources-container';

            const label = document.createElement('span');
            label.className = 'sources-label';
            label.textContent = 'PDF Sources:';
            sourcesDiv.appendChild(label);

            sources.forEach(page => {
                const badge = document.createElement('button');
                badge.type = 'button';
                badge.className = 'source-badge';
                badge.innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    </svg>
                    <span>Page ${page}</span>
                `;

                // Highlight only evidence the server verified for THIS page (see citations.py).
                // No page/score guessing: without verified evidence the badge just opens the page.
                const liveHash = currentDocument && currentDocument.hash;
                const pageSpecs = (citations || [])
                    .filter(c => c && c.page === page && c.evidence_verified && c.evidence)
                    .filter(c => !c.docHash || !liveHash || c.docHash === liveHash)
                    .map(c => ({ text: c.evidence, hint: (typeof c.position_hint === 'number') ? c.position_hint : null }));

                badge.addEventListener('click', () => showCitation(page, pageSpecs));

                sourcesDiv.appendChild(badge);
            });

            bubble.appendChild(sourcesDiv);
        }

        wrapper.appendChild(bubble);

        // ChatGPT-like AI Response Toolbar: Copy, Retry / Regenerate
        const toolbar = document.createElement('div');
        toolbar.className = 'msg-toolbar';

        // 1. Copy Response
        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'btn-msg-action btn-copy-response';
        copyBtn.setAttribute('aria-label', 'Copy response');
        copyBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span class="btn-popout-label">Copy</span>
        `;
        copyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            try {
                await navigator.clipboard.writeText(answerText);
                copyBtn.classList.add('copied');
                copyBtn.innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    <span class="btn-popout-label">Copied!</span>
                `;
                setTimeout(() => {
                    copyBtn.classList.remove('copied');
                    copyBtn.innerHTML = `
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span class="btn-popout-label">Copy</span>
                    `;
                }, 2000);
            } catch {
                showGlobalAlert('Unable to copy response to clipboard', 'warning');
            }
        });

        // 2. Retry / Regenerate Response
        const regenBtn = document.createElement('button');
        regenBtn.type = 'button';
        regenBtn.className = 'btn-msg-action btn-regenerate';
        regenBtn.setAttribute('aria-label', 'Regenerate response');
        regenBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            <span class="btn-popout-label">Regenerate</span>
        `;
        regenBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (isGenerating) return;

            let q = correspondingQuestion;
            if (!q) {
                const activeConv = conversations.find(c => c.id === activeConversationId);
                if (activeConv && activeConv.messages) {
                    let targetIdx = msgIndex;
                    if (targetIdx === null || targetIdx === undefined) {
                        targetIdx = activeConv.messages.findIndex(m => m.sender === 'assistant' && m.text === answerText);
                    }
                    if (targetIdx > 0) {
                        const prevUser = activeConv.messages.slice(0, targetIdx).reverse().find(m => m.sender === 'user');
                        if (prevUser) q = prevUser.text;
                    }
                }
            }

            if (!q) {
                showGlobalAlert('Could not identify question to regenerate.', 'warning');
                return;
            }

            if (!currentDocument) {
                showGlobalAlert('No active PDF loaded. Please upload a PDF before regenerating.', 'warning');
                return;
            }

            setGeneratingState(true);
            bubble.innerHTML = '<span class="loading-dots">Regenerating answer from PDF...</span>';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: q })
                });

                let data = null;
                const contentType = res.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    data = await res.json();
                } else {
                    const text = await res.text();
                    try { data = JSON.parse(text); } catch { data = { detail: text }; }
                }

                if (res.ok && data && data.answer) {
                    const activeConv = conversations.find(c => c.id === activeConversationId);
                    if (activeConv && activeConv.messages) {
                        let targetIdx = msgIndex;
                        if (targetIdx === null || targetIdx === undefined) {
                            targetIdx = activeConv.messages.findIndex(m => m.sender === 'assistant' && (m.text === answerText || m.question === q));
                        }
                        if (targetIdx !== -1 && targetIdx < activeConv.messages.length) {
                            activeConv.messages[targetIdx].text = data.answer;
                            activeConv.messages[targetIdx].sources = data.sources || [];
                            activeConv.messages[targetIdx].chunks = data.retrieved_chunks || [];
                            activeConv.messages[targetIdx].citations = stampCitations(data.citations);
                            activeConv.messages[targetIdx].question = q;
                            saveConversations();
                        }
                    }

                    const newWrapper = document.createElement('div');
                    newWrapper.className = 'message-wrapper assistant';
                    wrapper.replaceWith(newWrapper);
                    appendAssistantMessage(data.answer, data.sources, data.retrieved_chunks, q, msgIndex, stampCitations(data.citations));
                } else {
                    let errMsg = 'Failed to regenerate response.';
                    if (res.status === 429) {
                        errMsg = (data && data.detail) || 'AI model rate limit reached. Please wait a moment and try again.';
                    } else if (res.status === 503) {
                        errMsg = (data && data.detail) || 'AI model is currently experiencing high demand. Please try again shortly.';
                    } else if (data && (data.detail || data.message)) {
                        errMsg = data.detail || data.message;
                    }
                    bubble.className = 'message-bubble error';
                    bubble.innerHTML = `<p style="color: var(--danger);">${escapeHtml(errMsg)}</p>`;
                }
            } catch (err) {
                bubble.className = 'message-bubble error';
                bubble.innerHTML = `<p style="color: var(--danger);">Network error while regenerating: ${escapeHtml(err.message)}</p>`;
            } finally {
                setGeneratingState(false);
            }
        });

        toolbar.appendChild(copyBtn);
        toolbar.appendChild(regenBtn);
        wrapper.appendChild(toolbar);

        wrapper.addEventListener('click', (e) => {
            if (e.target.closest('.btn-msg-action') || e.target.closest('.source-badge')) return;
            wrapper.classList.toggle('touch-show');
        });

        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
        return wrapper;
    }

    function appendAssistantFallbackMessage(queryText, messageText) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble warning';
        bubble.innerHTML = `<p>${escapeHtml(messageText || 'The PDF context does not contain enough information to answer this question.')}</p>`;

        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '8px';
        actions.style.flexWrap = 'wrap';
        actions.style.marginTop = '10px';

        const fallbackBtn = document.createElement('button');
        fallbackBtn.type = 'button';
        fallbackBtn.className = 'btn-msg-action';
        fallbackBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v20"></path>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14.5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
            <span>Ask Gemini instead</span>
        `;
        fallbackBtn.addEventListener('click', async () => {
            if (isGenerating) return;
            setGeneratingState(true);
            fallbackBtn.disabled = true;
            fallbackBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v20"></path>
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14.5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
                <span>Using Gemini…</span>
            `;
            try {
                const res = await fetch('/api/chat/fallback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: queryText })
                });
                const data = await res.json().catch(() => ({ detail: 'Fallback request failed.' }));

                if (res.ok && data && data.answer) {
                    wrapper.remove();
                    recordMessageInActiveConversation('assistant', data.answer, [], [], queryText, []);
                    appendGeneralKnowledgeMessage(data.answer, queryText);
                } else {
                    const errMsg = (data && (data.detail || data.message)) || 'Gemini general-knowledge fallback failed.';
                    bubble.innerHTML = `<p style="color: var(--danger);">${escapeHtml(errMsg)}</p>`;
                    actions.innerHTML = '';
                    const retryBtn = document.createElement('button');
                    retryBtn.type = 'button';
                    retryBtn.className = 'btn-msg-action';
                    retryBtn.innerHTML = '<span>Retry</span>';
                    retryBtn.addEventListener('click', () => {
                        wrapper.remove();
                        appendAssistantFallbackMessage(queryText, messageText);
                    });
                    actions.appendChild(retryBtn);
                    bubble.appendChild(actions);
                }
            } catch (err) {
                bubble.innerHTML = `<p style="color: var(--danger);">${escapeHtml(err.message || 'General knowledge fallback failed.')}</p>`;
                actions.innerHTML = '';
                const retryBtn = document.createElement('button');
                retryBtn.type = 'button';
                retryBtn.className = 'btn-msg-action';
                retryBtn.innerHTML = '<span>Retry</span>';
                retryBtn.addEventListener('click', () => {
                    wrapper.remove();
                    appendAssistantFallbackMessage(queryText, messageText);
                });
                actions.appendChild(retryBtn);
                bubble.appendChild(actions);
            } finally {
                setGeneratingState(false);
            }
        });

        const retryBtn = document.createElement('button');
        retryBtn.type = 'button';
        retryBtn.className = 'btn-msg-action';
        retryBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            <span>Retry Question</span>
        `;
        retryBtn.addEventListener('click', () => {
            wrapper.remove();
            submitUserQuestion(queryText, null, false);
        });

        actions.appendChild(fallbackBtn);
        actions.appendChild(retryBtn);
        bubble.appendChild(actions);

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
    }

    function appendGeneralKnowledgeMessage(answerText, correspondingQuestion = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const label = document.createElement('div');
        label.className = 'general-knowledge-label';
        label.textContent = 'Gemini General Knowledge';
        label.style.fontSize = '11px';
        label.style.fontWeight = '700';
        label.style.letterSpacing = '0.08em';
        label.style.textTransform = 'uppercase';
        label.style.color = 'var(--accent)';
        label.style.marginBottom = '8px';
        bubble.appendChild(label);

        const textContainer = document.createElement('div');
        textContainer.className = 'assistant-text-content';
        textContainer.innerHTML = formatMarkdownText(answerText);
        bubble.appendChild(textContainer);

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
    }

    function appendAssistantNoAnswerMessage(queryText, messageText) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble warning';
        bubble.innerHTML = `<p>${escapeHtml(messageText || 'The PDF context does not contain enough information to answer this question.')}</p>`;

        if (queryText) {
            const retryAction = document.createElement('div');
            retryAction.style.marginTop = '8px';
            const retryBtn = document.createElement('button');
            retryBtn.type = 'button';
            retryBtn.className = 'btn-msg-action';
            retryBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                <span>Retry Question</span>
            `;
            retryBtn.addEventListener('click', () => {
                wrapper.remove();
                submitUserQuestion(queryText, null, false);
            });
            retryAction.appendChild(retryBtn);
            bubble.appendChild(retryAction);
        }

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
    }

    function appendAssistantErrorMessage(errorText, correspondingQuestion = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble error';
        bubble.innerHTML = `<p style="color: var(--danger);">${escapeHtml(errorText)}</p>`;

        if (correspondingQuestion) {
            const retryAction = document.createElement('div');
            retryAction.style.marginTop = '8px';
            const retryBtn = document.createElement('button');
            retryBtn.type = 'button';
            retryBtn.className = 'btn-msg-action';
            retryBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                <span>Retry</span>
            `;
            retryBtn.addEventListener('click', () => {
                wrapper.remove();
                submitUserQuestion(correspondingQuestion, null, false);
            });
            retryAction.appendChild(retryBtn);
            bubble.appendChild(retryAction);
        }

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToChatBottom();
    }

    function formatMarkdownText(text) {
        return window.CWPMarkdown.render(text || '');
    }

    function scrollToChatBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // --------------------------------------------------------------------------
    // 11. Image Attachment & Voice Recognition Setup
    // --------------------------------------------------------------------------

    btnAttach?.addEventListener('click', () => imageFileInput?.click());

    imageFileInput?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                showGlobalAlert('Please select a valid image file.', 'warning');
                return;
            }
            selectedImageFile = file;
            if (attachmentImg) attachmentImg.src = URL.createObjectURL(file);
            if (attachmentName) attachmentName.textContent = file.name;
            if (attachmentSize) attachmentSize.textContent = `${Math.round(file.size / 1024)} KB`;
            if (attachmentPreview) attachmentPreview.style.display = 'flex';
        }
    });

    btnRemoveAttachment?.addEventListener('click', clearAttachmentPreview);

    function clearAttachmentPreview() {
        selectedImageFile = null;
        if (imageFileInput) imageFileInput.value = '';
        if (attachmentPreview) attachmentPreview.style.display = 'none';
    }

    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            if (btnMic) btnMic.title = 'Speech recognition not supported in this browser';
            return;
        }

        try {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                isListening = true;
                if (btnMic) {
                    btnMic.classList.add('active', 'recording');
                }
                if (voiceRecordingBar) voiceRecordingBar.style.display = 'flex';
                if (voiceStatusText) voiceStatusText.textContent = 'Listening...';
                if (voiceFinalText) voiceFinalText.textContent = '';
                if (voiceInterimText) voiceInterimText.textContent = 'Speak now...';

                speechBaseText = questionInput ? questionInput.value : '';
                speechFinalText = '';
            };

            recognition.onresult = (event) => {
                let currentInterim = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    const res = event.results[i];
                    if (res.isFinal) {
                        const chunk = res[0].transcript.trim();
                        if (chunk) {
                            speechFinalText = speechFinalText ? `${speechFinalText} ${chunk}` : chunk;
                        }
                    } else {
                        currentInterim += res[0].transcript;
                    }
                }

                if (voiceStatusText) {
                    voiceStatusText.textContent = (currentInterim || speechFinalText) ? 'Transcribing...' : 'Listening...';
                }

                // 1. Live preview inside voice recording bar
                if (voiceFinalText) voiceFinalText.textContent = speechFinalText;
                if (voiceInterimText) {
                    voiceInterimText.textContent = currentInterim ? ` ${currentInterim}` : (!speechFinalText ? 'Speak now...' : '');
                }

                // 2. Real-time preview inside questionInput (words shown outside, like Claude)
                if (questionInput) {
                    const fullSpoken = (speechFinalText + (currentInterim ? ' ' + currentInterim : '')).trim();
                    const combined = speechBaseText ? `${speechBaseText} ${fullSpoken}` : fullSpoken;
                    questionInput.value = combined;
                }
            };

            recognition.onerror = (e) => {
                console.warn('Speech recognition status:', e.error);
                if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                    showGlobalAlert('Microphone access not granted.', 'warning');
                    stopListening(false);
                }
            };

            recognition.onend = () => {
                if (isListening) {
                    stopListening(true);
                }
            };

            btnMic?.addEventListener('click', () => {
                if (isListening) {
                    stopListening(true);
                } else {
                    startListening();
                }
            });

            btnVoiceDone?.addEventListener('click', () => {
                stopListening(true);
            });

            btnVoiceCancel?.addEventListener('click', () => {
                stopListening(false);
            });
        } catch (err) {
            console.error('Error initializing Speech Recognition:', err);
        }
    }

    function startListening() {
        if (!recognition || isListening) return;
        try {
            recognition.start();
        } catch (e) {
            console.warn('Speech start error:', e);
        }
    }

    function stopListening(commit = true) {
        if (!isListening && (!voiceRecordingBar || voiceRecordingBar.style.display === 'none')) return;
        isListening = false;

        if (btnMic) {
            btnMic.classList.remove('active', 'recording');
        }
        if (voiceRecordingBar) {
            voiceRecordingBar.style.display = 'none';
        }

        if (recognition) {
            try {
                recognition.stop();
            } catch (e) { }
        }

        if (!commit && questionInput) {
            questionInput.value = speechBaseText;
        }

        if (questionInput) {
            questionInput.focus();
        }
    }

    // --------------------------------------------------------------------------
    // 12. Modal & Alert System & Customized Answer Engine
    // --------------------------------------------------------------------------

    const btnOpenCustomStructure = document.getElementById('btnOpenCustomStructure');
    const customAnswerModal = document.getElementById('customAnswerModal');
    const btnCloseCustomStructure = document.getElementById('btnCloseCustomStructure');
    const btnCloseCustomStructureBottom = document.getElementById('btnCloseCustomStructureBottom');
    const btnApplyCustomStructure = document.getElementById('btnApplyCustomStructure');
    const btnRemoveCustomStructure = document.getElementById('btnRemoveCustomStructure');
    const customStructureInput = document.getElementById('customStructureInput');
    const customStructureActiveDot = document.getElementById('customStructureActiveDot');

    const PRESET_FORMATS = {
        short: 'Format answer in Short Form: 2 to 3 concise bullet points with bold key terms and no fluff.',
        exec: 'Format answer as an Executive Brief: 1-sentence Direct Summary followed by Key Takeaways in bullet points.',
        steps: 'Format answer as a Step-by-Step Breakdown with numbered items and bold subheadings.',
        academic: 'Format answer as a Detailed Analysis: Use clear Markdown section headings (###), in-depth explanations, and page citations.'
    };

    function checkActiveCustomStructure() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const mem = (data.answer_memory?.text || '').trim();
                if (mem) {
                    if (customStructureActiveDot) customStructureActiveDot.style.display = 'inline-block';
                    if (customStructureInput && !customStructureInput.value.trim()) {
                        customStructureInput.value = mem;
                    }
                } else {
                    if (customStructureActiveDot) customStructureActiveDot.style.display = 'none';
                }
            })
            .catch(() => { });
    }

    checkActiveCustomStructure();

    btnOpenCustomStructure?.addEventListener('click', () => {
        if (customAnswerModal) customAnswerModal.style.display = 'flex';
        checkActiveCustomStructure();
    });

    btnCloseCustomStructure?.addEventListener('click', () => {
        if (customAnswerModal) customAnswerModal.style.display = 'none';
    });

    btnCloseCustomStructureBottom?.addEventListener('click', () => {
        if (customAnswerModal) customAnswerModal.style.display = 'none';
    });

    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-preset');
            if (PRESET_FORMATS[key] && customStructureInput) {
                customStructureInput.value = PRESET_FORMATS[key];
            }
        });
    });

    btnApplyCustomStructure?.addEventListener('click', async () => {
        const text = customStructureInput ? customStructureInput.value.trim() : '';
        if (!text) {
            showGlobalAlert('Please select a preset or type format instructions before applying.', 'warning');
            return;
        }

        try {
            const res = await fetch('/api/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memory: text })
            });

            if (res.ok) {
                if (customStructureActiveDot) customStructureActiveDot.style.display = 'inline-block';
                if (customAnswerModal) customAnswerModal.style.display = 'none';
                showGlobalAlert('Customized Answer Structure applied successfully!', 'success');
            } else {
                showGlobalAlert('Failed to save structure preference.', 'error');
            }
        } catch (e) {
            showGlobalAlert('Network error applying structure.', 'error');
        }
    });

    btnRemoveCustomStructure?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memory: '' })
            });

            if (res.ok) {
                if (customStructureInput) customStructureInput.value = '';
                if (customStructureActiveDot) customStructureActiveDot.style.display = 'none';
                if (customAnswerModal) customAnswerModal.style.display = 'none';
                showGlobalAlert('Customized Answer Structure removed. Reverted to standard format.', 'info');
            } else {
                showGlobalAlert('Could not clear structure.', 'error');
            }
        } catch (e) {
            showGlobalAlert('Error removing structure.', 'error');
        }
    });

    function showSettingsModal() {
        if (settingsModal) settingsModal.style.display = 'flex';
        updateSettingsDocUI();
        loadSettingsValues();
    }

    btnCloseSettings?.addEventListener('click', () => {
        if (settingsModal) settingsModal.style.display = 'none';
    });

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');

            btn.classList.add('active');
            const targetEl = document.getElementById(targetTab);
            if (targetEl) targetEl.style.display = 'block';
        });
    });

    // Settings Modal Inputs
    const settingTopK = document.getElementById('settingTopK');
    const topKValueDisplay = document.getElementById('topKValueDisplay');
    const btnSaveMemorySetting = document.getElementById('btnSaveMemorySetting');
    const settingAnswerMemory = document.getElementById('settingAnswerMemory');

    settingTopK?.addEventListener('input', (e) => {
        if (topKValueDisplay) topKValueDisplay.textContent = e.target.value;
        localStorage.setItem('cwp_top_k', e.target.value);
    });

    btnSaveMemorySetting?.addEventListener('click', async () => {
        const memoryText = settingAnswerMemory ? settingAnswerMemory.value.trim() : '';
        try {
            await fetch('/api/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memory: memoryText })
            });
            showGlobalAlert('Answer formatting rule saved successfully.', 'success');
        } catch (e) {
            showGlobalAlert('Failed to save memory rule.', 'error');
        }
    });

    function loadSettingsValues() {
        const savedTopK = localStorage.getItem('cwp_top_k') || '6';
        if (settingTopK) settingTopK.value = savedTopK;
        if (topKValueDisplay) topKValueDisplay.textContent = savedTopK;

        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                if (settingAnswerMemory && data.answer_memory) {
                    settingAnswerMemory.value = data.answer_memory.text || '';
                }
            })
            .catch(() => { });
    }

    function showGlobalAlert(message, type = 'info') {
        if (!alertBanner || !alertText) return;
        alertText.textContent = message;
        alertBanner.className = `alert-banner ${type}`;
        alertBanner.style.display = 'block';

        setTimeout(() => {
            if (alertBanner) alertBanner.style.display = 'none';
        }, 5000);
    }

    alertCloseBtn?.addEventListener('click', () => {
        if (alertBanner) alertBanner.style.display = 'none';
    });

    // --------------------------------------------------------------------------
    // 13. Conversation Storage & History Management Engine
    // --------------------------------------------------------------------------

    async function initConversationState() {
        try {
            const response = await fetch('/api/conversations', { cache: 'no-store' });
            if (response.ok) {
                const data = await response.json();
                conversations = Array.isArray(data.conversations) ? data.conversations : [];
                conversationDocumentHash = data.document_hash || null;
                if (conversations.length === 0 && localStorage.getItem('cwp_conversations_migrated') !== '1') {
                    const configResponse = await fetch('/api/config', { cache: 'no-store' });
                    const config = configResponse.ok ? await configResponse.json() : {};
                    if (config.local_history_migration_enabled) {
                        const legacy = JSON.parse(localStorage.getItem('cwp_conversations') || '[]');
                        if (Array.isArray(legacy) && legacy.length > 0) {
                            const saved = await fetch('/api/conversations', {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ conversations: legacy, document_hash: conversationDocumentHash })
                            });
                            if (!saved.ok) throw new Error('Legacy conversation migration failed.');
                            conversations = legacy;
                            localStorage.removeItem('cwp_conversations');
                        }
                        localStorage.setItem('cwp_conversations_migrated', '1');
                    }
                }
            }
        } catch (err) {
            console.warn('Could not load this session conversation history.');
        }

        if (conversations.length === 0) {
            createNewConversation();
        } else {
            activeConversationId = conversations[0].id;
            renderChatHistoryList();
            loadActiveConversationMessages();
        }

        btnNewChat?.addEventListener('click', () => createNewConversation());
    }

    function createNewConversation() {
        const newId = 'conv_' + Date.now();
        const newConv = {
            id: newId,
            title: 'New Conversation',
            createdAt: new Date().toISOString(),
            pinned: false,
            messages: []
        };
        conversations.unshift(newConv);
        activeConversationId = newId;
        saveConversations();
        renderChatHistoryList();

        if (chatMessages) {
            chatMessages.innerHTML = '';
            if (welcomeCard) chatMessages.appendChild(welcomeCard);
        }
        if (welcomeCard) welcomeCard.style.display = 'block';
    }

    function autoTitleActiveConversation(questionText) {
        const activeConv = conversations.find(c => c.id === activeConversationId);
        if (activeConv && (activeConv.title === 'New Conversation' || activeConv.title === 'New Chat' || !activeConv.title)) {
            let title = questionText.replace(/[?.,!]/g, '').trim();
            const words = title.split(/\s+/);
            if (words.length > 5) {
                title = words.slice(0, 5).join(' ') + '...';
            }
            if (title.length > 28) {
                title = title.substring(0, 28) + '...';
            }
            activeConv.title = title.charAt(0).toUpperCase() + title.slice(1);
            saveConversations();
            renderChatHistoryList();
        }
    }

    // Tag server citations with the document they belong to, so an old badge can never
    // highlight against a different PDF after a new upload.
    function stampCitations(citations) {
        const hash = currentDocument && currentDocument.hash ? currentDocument.hash : null;
        return (citations || []).map(c => Object.assign({}, c, { docHash: hash }));
    }

    function recordMessageInActiveConversation(sender, text, sources = [], chunks = [], question = null, citations = []) {
        let activeConv = conversations.find(c => c.id === activeConversationId);
        if (!activeConv) {
            createNewConversation();
            activeConv = conversations.find(c => c.id === activeConversationId);
        }
        if (!activeConv.messages) activeConv.messages = [];
        activeConv.messages.push({
            sender,
            text,
            sources,
            chunks,
            citations,
            question,
            timestamp: new Date().toISOString()
        });
        saveConversations();
    }

    function loadActiveConversationMessages() {
        if (!chatMessages) return;
        chatMessages.innerHTML = '';
        const activeConv = conversations.find(c => c.id === activeConversationId);
        if (!activeConv || !activeConv.messages || activeConv.messages.length === 0) {
            if (welcomeCard) chatMessages.appendChild(welcomeCard);
            if (welcomeCard) welcomeCard.style.display = 'block';
            return;
        }

        if (welcomeCard) welcomeCard.style.display = 'none';

        activeConv.messages.forEach((msg, idx) => {
            if (msg.sender === 'user') {
                appendUserMessage(msg.text, null, idx);
            } else {
                const prevUser = activeConv.messages.slice(0, idx).reverse().find(m => m.sender === 'user');
                const q = msg.question || (prevUser ? prevUser.text : null);
                appendAssistantMessage(msg.text, msg.sources, msg.chunks, q, idx, msg.citations);
            }
        });
        scrollToChatBottom();
    }

    function renderChatHistoryList() {
        if (!chatHistoryList) return;
        chatHistoryList.innerHTML = '';

        if (conversations.length === 0) {
            chatHistoryList.innerHTML = '<div class="history-empty-text">No previous conversations.</div>';
            return;
        }

        // Sort conversations: pinned items first
        const sortedConvs = [...conversations].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

        sortedConvs.forEach(conv => {
            const isSelected = conv.id === activeConversationId;
            const item = document.createElement('div');
            item.className = `history-item ${isSelected ? 'active' : ''} ${conv.pinned ? 'pinned' : ''}`;

            const leftContainer = document.createElement('div');
            leftContainer.className = 'history-item-left';
            leftContainer.innerHTML = `
                <svg class="chat-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <svg class="history-pin-indicator" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" title="Pinned conversation">
                    <line x1="12" y1="17" x2="12" y2="22"></line>
                    <path d="M5 17h14l-1.5-6H6.5L5 17z"></path>
                    <path d="M9 11V4a3 3 0 0 1 6 0v7"></path>
                </svg>
                <span class="history-item-title" title="${escapeHtml(conv.title)}">${escapeHtml(conv.title)}</span>
            `;

            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'history-item-actions';

            // 1. Pin Action
            const pinBtn = document.createElement('button');
            pinBtn.type = 'button';
            pinBtn.className = 'btn-history-action btn-pin';
            pinBtn.title = conv.pinned ? 'Unpin conversation' : 'Pin conversation';
            pinBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="${conv.pinned ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="17" x2="12" y2="22"></line>
                    <path d="M5 17h14l-1.5-6H6.5L5 17z"></path>
                    <path d="M9 11V4a3 3 0 0 1 6 0v7"></path>
                </svg>
            `;
            pinBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                conv.pinned = !conv.pinned;
                saveConversations();
                renderChatHistoryList();
            });

            // 2. Share Action
            const shareBtn = document.createElement('button');
            shareBtn.type = 'button';
            shareBtn.className = 'btn-history-action btn-share';
            shareBtn.title = 'Share conversation';
            shareBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="18" cy="5" r="3"></circle>
                    <circle cx="6" cy="12" r="3"></circle>
                    <circle cx="18" cy="19" r="3"></circle>
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
            `;
            shareBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                shareConversation(conv);
            });

            // 3. Download Action
            const downloadBtn = document.createElement('button');
            downloadBtn.type = 'button';
            downloadBtn.className = 'btn-history-action btn-download';
            downloadBtn.title = 'Download conversation';
            downloadBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
            `;
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                exportConversation(conv);
            });

            // 4. Delete Action
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'btn-history-action btn-delete danger';
            deleteBtn.title = 'Delete conversation';
            deleteBtn.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            `;
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm(`Delete conversation "${conv.title}"?`)) {
                    conversations = conversations.filter(c => c.id !== conv.id);
                    if (activeConversationId === conv.id) {
                        activeConversationId = conversations.length > 0 ? conversations[0].id : null;
                    }
                    saveConversations();
                    renderChatHistoryList();
                    if (activeConversationId) {
                        loadActiveConversationMessages();
                    } else {
                        createNewConversation();
                    }
                }
            });

            actionsContainer.appendChild(pinBtn);
            actionsContainer.appendChild(shareBtn);
            actionsContainer.appendChild(downloadBtn);
            actionsContainer.appendChild(deleteBtn);

            // Touch accessible trigger for mobile/touch screens
            const touchBtn = document.createElement('button');
            touchBtn.type = 'button';
            touchBtn.className = 'history-touch-trigger';
            touchBtn.title = 'Conversation options';
            touchBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="1.5"></circle>
                    <circle cx="12" cy="5" r="1.5"></circle>
                    <circle cx="12" cy="19" r="1.5"></circle>
                </svg>
            `;
            touchBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showConversationActionMenu(conv, item, e);
            });

            item.appendChild(leftContainer);
            item.appendChild(actionsContainer);
            item.appendChild(touchBtn);

            item.addEventListener('click', () => {
                if (activeConversationId !== conv.id) {
                    activeConversationId = conv.id;
                    renderChatHistoryList();
                    loadActiveConversationMessages();
                }
            });

            chatHistoryList.appendChild(item);
        });
    }

    function showConversationActionMenu(conv, item, e) {
        document.querySelectorAll('.history-touch-popover').forEach(el => el.remove());
        const popover = document.createElement('div');
        popover.className = 'history-touch-popover';
        popover.innerHTML = `
            <button type="button" class="touch-popover-item" data-action="pin">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="${conv.pinned ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14l-1.5-6H6.5L5 17z"></path><path d="M9 11V4a3 3 0 0 1 6 0v7"></path></svg>
                <span>${conv.pinned ? 'Unpin' : 'Pin'}</span>
            </button>
            <button type="button" class="touch-popover-item" data-action="share">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                <span>Share</span>
            </button>
            <button type="button" class="touch-popover-item" data-action="download">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                <span>Download</span>
            </button>
            <button type="button" class="touch-popover-item danger" data-action="delete">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                <span>Delete</span>
            </button>
        `;

        popover.addEventListener('click', (ev) => {
            ev.stopPropagation();
            const btn = ev.target.closest('.touch-popover-item');
            if (!btn) return;
            const action = btn.dataset.action;
            popover.remove();

            if (action === 'pin') {
                conv.pinned = !conv.pinned;
                saveConversations();
                renderChatHistoryList();
            } else if (action === 'share') {
                shareConversation(conv);
            } else if (action === 'download') {
                exportConversation(conv);
            } else if (action === 'delete') {
                if (confirm(`Delete conversation "${conv.title}"?`)) {
                    conversations = conversations.filter(c => c.id !== conv.id);
                    if (activeConversationId === conv.id) {
                        activeConversationId = conversations.length > 0 ? conversations[0].id : null;
                    }
                    saveConversations();
                    renderChatHistoryList();
                    if (activeConversationId) {
                        loadActiveConversationMessages();
                    } else {
                        createNewConversation();
                    }
                }
            }
        });

        item.appendChild(popover);
        const closeHandler = (event) => {
            if (!popover.contains(event.target)) {
                popover.remove();
                document.removeEventListener('click', closeHandler);
            }
        };
        setTimeout(() => document.addEventListener('click', closeHandler), 10);
    }

    async function shareConversation(conv) {
        let text = `# ${conv.title}\n\n`;
        if (conv.messages && conv.messages.length) {
            conv.messages.forEach(msg => {
                text += `### ${msg.sender === 'user' ? 'User' : 'Assistant'}\n${msg.text}\n\n`;
            });
        } else {
            text += `No messages in conversation.\n`;
        }

        if (navigator.share) {
            try {
                await navigator.share({
                    title: conv.title,
                    text: text,
                    url: window.location.href
                });
                showGlobalAlert(`Conversation "${conv.title}" shared successfully.`, 'success');
                return;
            } catch (err) {
                if (err.name === 'AbortError') return;
            }
        }

        try {
            await navigator.clipboard.writeText(text);
            showGlobalAlert(`Conversation "${conv.title}" transcript copied to clipboard for sharing.`, 'success');
        } catch {
            showGlobalAlert('Unable to copy conversation to clipboard.', 'warning');
        }
    }

    function exportConversation(conv) {
        let text = `# ${conv.title}\n\n`;
        if (conv.messages && conv.messages.length) {
            conv.messages.forEach(msg => {
                text += `### ${msg.sender === 'user' ? 'User' : 'Assistant'}\n${msg.text}\n\n`;
            });
        } else {
            text += `No messages in conversation.\n`;
        }

        const blob = new Blob([text], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${conv.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_export.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function saveConversations() {
        const body = JSON.stringify({ conversations, document_hash: conversationDocumentHash });
        conversationSaveQueue = conversationSaveQueue
            .catch(() => {})
            .then(async () => {
                const response = await fetch('/api/conversations', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body
                });
                if (!response.ok) throw new Error('Conversation history could not be saved.');
            })
            .catch(() => console.warn('Could not save this session conversation history.'));
    }
});
