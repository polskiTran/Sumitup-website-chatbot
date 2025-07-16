/**
 * PocketFlow Chatbot - Standalone Embeddable Chatbot
 *
 * Usage:
 * <script src="chatbot.js"></script>
 * <script>
 * document.addEventListener('DOMContentLoaded', () => {
 *     initializeChatbot({
 *         current_url: 'https://example.com',
 *         extra_urls: ['https://example.com/docs', 'https://example.com/help'],
 *         prefixes: [],
 *         chatbotName: 'PocketFlow Website Chatbot',
 *         wsUrl: 'ws://localhost:8000/api/ws/chat',
 *         instruction: 'You are a helpful website assistant.',
 *         isOpen: false,
 *         theme: 'auto' // 'auto', 'light', 'dark' - auto detects from page
 *     });
 * });
 * </script>
 */

function initializeChatbot(config) {
  const {
    current_url = "",
    extra_urls = [],
    prefixes = [],
    chatbotName = "PocketFlow Website Chatbot",
    wsUrl = "/api/ws/chat",
    instruction = "",
    isOpen = false,
    theme = "auto",
  } = config;

  // Store original config for URL updates
  window._pocketflowOriginalConfig = config;

  // Track if current_url was explicitly provided
  const wasCurrentUrlProvided = Boolean(current_url);

  // Handle current_url being empty - use current page URL
  let finalCurrentUrl = current_url;
  if (!finalCurrentUrl) {
    finalCurrentUrl = window.location.href;
  }

  // Theme detection and configuration
  let currentTheme = "light"; // Default theme

  // Simplified theme detection
  function detectTheme() {
    if (theme === "light" || theme === "dark") return theme;

    const html = document.documentElement;
    const body = document.body;

    // Check common theme attributes and classes
    const themeChecks = [
      () => html.getAttribute("data-theme"),
      () => html.getAttribute("data-color-scheme"),
      () => html.getAttribute("data-bs-theme"),
      () =>
        ["dark", "dark-theme", "theme-dark", "dark-mode"].find((cls) =>
          html.classList.contains(cls)
        )
          ? "dark"
          : null,
      () =>
        ["dark", "dark-theme", "theme-dark", "dark-mode"].find((cls) =>
          body.classList.contains(cls)
        )
          ? "dark"
          : null,
      () =>
        window.matchMedia?.("(prefers-color-scheme: dark)").matches
          ? "dark"
          : null,
    ];

    for (const check of themeChecks) {
      const result = check();
      if (result === "dark") return "dark";
      if (result === "light") return "light";
    }

    return "light";
  }

  // Update chatbot theme
  function updateChatbotTheme(newTheme) {
    currentTheme = newTheme;
    const elements = [
      document.getElementById("pocketflow-chat-icon"),
      document.getElementById("pocketflow-chat-window"),
    ];

    elements.forEach((el) => el?.setAttribute("data-chatbot-theme", newTheme));
  }

  // Watch for theme changes
  function setupThemeObserver() {
    const checkThemeChange = () => {
      const newTheme = detectTheme();
      if (newTheme !== currentTheme) {
        updateChatbotTheme(newTheme);
      }
    };

    // Watch for attribute and class changes
    const observer = new MutationObserver(checkThemeChange);
    [document.documentElement, document.body].forEach((el) => {
      observer.observe(el, {
        attributes: true,
        attributeFilter: [
          "data-theme",
          "data-color-scheme",
          "data-bs-theme",
          "class",
        ],
      });
    });

    // Watch system theme changes
    window
      .matchMedia?.("(prefers-color-scheme: dark)")
      .addEventListener("change", checkThemeChange);
  }

  // Detect initial theme
  currentTheme = detectTheme();

  // Inject CSS styles
  const chatbotStyles = `
        /* --- CHATBOT THEME VARIABLES --- */
        :root, html[data-theme="light"] {
            --chatbot-background: hsl(0 0% 100%);
            --chatbot-foreground: hsl(222.2 84% 4.9%);
            --chatbot-card: hsl(0 0% 100%);
            --chatbot-card-foreground: hsl(222.2 84% 4.9%);
            --chatbot-primary: hsl(222.2 47.4% 11.2%);
            --chatbot-primary-foreground: hsl(210 40% 98%);
            --chatbot-secondary: hsl(210 40% 96.1%);
            --chatbot-secondary-foreground: hsl(222.2 47.4% 11.2%);
            --chatbot-muted: hsl(210 40% 96.1%);
            --chatbot-muted-foreground: hsl(215.4 16.3% 46.9%);
            --chatbot-accent: hsl(210 40% 96.1%);
            --chatbot-accent-foreground: hsl(222.2 47.4% 11.2%);
            --chatbot-border: hsl(214.3 31.8% 91.4%);
            --chatbot-input: hsl(214.3 31.8% 91.4%);
            --chatbot-ring: hsl(222.2 84% 4.9%);
            --chatbot-radius: 1rem;
            --chatbot-primary-glow: hsl(222.2 47.4% 11.2% / 0.3);
        }

        /* Support multiple dark theme systems */
        html[data-theme="dark"],
        html.dark,
        .dark,
        [data-color-scheme="dark"],
        [data-bs-theme="dark"] {
            --chatbot-background: hsl(222.2 84% 4.9%);
            --chatbot-foreground: hsl(210 40% 98%);
            --chatbot-card: hsl(222.2 84% 4.9%);
            --chatbot-card-foreground: hsl(210 40% 98%);
            --chatbot-primary: hsl(210 40% 98%);
            --chatbot-primary-foreground: hsl(222.2 47.4% 11.2%);
            --chatbot-secondary: hsl(217.2 32.6% 17.5%);
            --chatbot-secondary-foreground: hsl(210 40% 98%);
            --chatbot-muted: hsl(217.2 32.6% 17.5%);
            --chatbot-muted-foreground: hsl(215 20.2% 65.1%);
            --chatbot-accent: hsl(217.2 32.6% 17.5%);
            --chatbot-accent-foreground: hsl(210 40% 98%);
            --chatbot-border: hsl(217.2 32.6% 17.5%);
            --chatbot-input: hsl(217.2 32.6% 17.5%);
            --chatbot-ring: hsl(212.7 26.8% 83.9%);
            --chatbot-primary-glow: hsl(212.7 26.8% 83.9% / 0.25);
        }

        /* --- CHATBOT RESET - Ensure consistent styling --- */
        #pocketflow-chat-window,
        #pocketflow-chat-window *,
        #pocketflow-chat-window *::before,
        #pocketflow-chat-window *::after,
        #pocketflow-chat-icon {
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* --- CHATBOT ANIMATIONS --- */
        @keyframes chatbot-pulse-glow {
            0% {
                transform: scale(1);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), 0 0 0 0px var(--chatbot-primary-glow);
            }
            50% {
                transform: scale(1.05);
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15), 0 0 0 12px transparent;
            }
            100% {
                transform: scale(1);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), 0 0 0 0px var(--chatbot-primary-glow);
            }
        }

        @keyframes chatbot-typing {
            0%, 80%, 100% { opacity: 0.3; }
            40% { opacity: 1; }
        }

        /* --- CHATBOT ICON --- */
        #pocketflow-chat-icon {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: var(--chatbot-primary, hsl(222.2 47.4% 11.2%));
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            z-index: 999998;
            border: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            animation: chatbot-pulse-glow 2.5s infinite cubic-bezier(0.4, 0, 0.2, 1);
        }

        #pocketflow-chat-icon:hover {
            animation: none;
            transform: scale(1.1);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        }

        /* Universal dark theme icon switching */
        #pocketflow-chat-icon .light-icon { display: block; }
        #pocketflow-chat-icon .dark-icon { display: none; }
        
        html[data-theme="dark"] #pocketflow-chat-icon .light-icon,
        html.dark #pocketflow-chat-icon .light-icon,
        .dark #pocketflow-chat-icon .light-icon,
        [data-color-scheme="dark"] #pocketflow-chat-icon .light-icon,
        [data-bs-theme="dark"] #pocketflow-chat-icon .light-icon { 
            display: none; 
        }
        
        html[data-theme="dark"] #pocketflow-chat-icon .dark-icon,
        html.dark #pocketflow-chat-icon .dark-icon,
        .dark #pocketflow-chat-icon .dark-icon,
        [data-color-scheme="dark"] #pocketflow-chat-icon .dark-icon,
        [data-bs-theme="dark"] #pocketflow-chat-icon .dark-icon { 
            display: block; 
        }
        
        #pocketflow-chat-icon svg {
            width: 32px;
            height: 32px;
            stroke: var(--chatbot-primary-foreground, hsl(210 40% 98%));
        }

        /* --- CHAT WINDOW --- */
        #pocketflow-chat-window {
            position: fixed;
            bottom: 110px;
            right: 30px;
            width: 380px;
            max-width: calc(100vw - 48px);
            height: 70vh;
            max-height: 580px;
            background-color: var(--chatbot-card, hsl(0 0% 100%));
            border: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
            border-radius: var(--chatbot-radius, 1rem);
            box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
            display: none;
            flex-direction: column;
            z-index: 999999;
            opacity: 0;
            transform: translateY(20px) scale(0.95);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
        }

        #pocketflow-chat-window.open { 
            display: flex; 
            opacity: 1; 
            transform: translateY(0) scale(1); 
        }

        #pocketflow-chat-window.maximized {
            bottom: 0;
            right: 0;
            width: 100vw;
            height: 100vh;
            max-width: 100vw;
            max-height: 100vh;
            border-radius: 0;
        }

        /* --- CHAT HEADER --- */
        #pocketflow-chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--chatbot-card, hsl(0 0% 100%));
            color: var(--chatbot-foreground, hsl(222.2 84% 4.9%));
            padding: 12px 16px;
            border-bottom: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
            font-weight: 600;
            font-size: 16px;
            flex-shrink: 0;
        }

        #pocketflow-chat-header .header-title { 
            flex-grow: 1; 
            text-align: center; 
            margin-left: 32px;
        }

        .pocketflow-chat-header-button {
            background: none; 
            border: none; 
            padding: 4px; 
            cursor: pointer;
            width: 24px; 
            height: 24px; 
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
        }

        .pocketflow-chat-header-button:hover { 
            color: var(--chatbot-foreground, hsl(222.2 84% 4.9%)); 
        }

        .pocketflow-chat-header-button svg { 
            width: 100%; 
            height: 100%; 
        }
        
        #pocketflow-connection-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            transition: background-color 0.3s ease;
            flex-shrink: 0;
            margin-right: -20px;
            margin-left: 20px;
        }
        
        .pocketflow-status-connected { background-color: hsl(142.1, 76.2%, 41.2%); }
        .pocketflow-status-connecting { background-color: hsl(47.9, 95.8%, 53.1%); }
        .pocketflow-status-disconnected { background-color: hsl(0, 84.2%, 60.2%); }

        /* --- CHAT MESSAGES --- */
        #pocketflow-chat-messages {
            flex-grow: 1;
            padding: 16px;
            overflow-y: auto;
            background-color: var(--chatbot-background, hsl(0 0% 100%));
        }

        /* Enhanced left padding for maximized chat window */
        #pocketflow-chat-window.maximized #pocketflow-chat-header {
            padding: 12px 16px 12px 60px;
        }

        #pocketflow-chat-window.maximized #pocketflow-chat-messages {
            padding: 16px 16px 16px 60px;
        }

        #pocketflow-chat-window.maximized #pocketflow-chat-input-area {
            padding: 12px 16px 12px 60px;
        }

        #pocketflow-chat-window.maximized .pocketflow-typing-indicator {
            padding: 0 14px 0 60px;
        }

        #pocketflow-chat-messages::-webkit-scrollbar { width: 6px; }
        #pocketflow-chat-messages::-webkit-scrollbar-track { background: transparent; }
        #pocketflow-chat-messages::-webkit-scrollbar-thumb { 
            background-color: var(--chatbot-border, hsl(214.3 31.8% 91.4%)); 
            border-radius: 3px; 
        }

        .pocketflow-context-banner {
            font-size: 12px;
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
            text-align: center;
            margin-bottom: 16px;
            padding: 8px 12px;
            background-color: var(--chatbot-muted, hsl(210 40% 96.1%));
            border-radius: 0.5rem;
            word-break: break-all;
            border: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
        }

        .pocketflow-context-banner strong {
            color: var(--chatbot-foreground, hsl(222.2 84% 4.9%));
        }

        .pocketflow-message {
            margin-bottom: 12px;
            padding: 10px 14px;
            border-radius: 1rem;
            max-width: 80%;
            line-height: 1.4;
            font-size: 14px;
            word-wrap: break-word;
            clear: both;
        }

        .pocketflow-message.user {
            background-color: var(--chatbot-primary, hsl(222.2 47.4% 11.2%));
            color: var(--chatbot-primary-foreground, hsl(210 40% 98%));
            float: right;
            margin-left: auto;
            border-bottom-right-radius: 0.25rem;
        }

        .pocketflow-message.bot {
            background-color: var(--chatbot-secondary, hsl(210 40% 96.1%));
            color: var(--chatbot-secondary-foreground, hsl(222.2 47.4% 11.2%));
            float: left;
            margin-right: auto;
            border-bottom-left-radius: 0.25rem;
        }

        .pocketflow-message.system {
            background-color: var(--chatbot-muted, hsl(210 40% 96.1%));
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
            float: none;
            margin: 8px auto;
            max-width: 90%;
            text-align: center;
            font-size: 13px;
            font-style: italic;
            border-radius: 1rem;
        }

        .pocketflow-message.bot h1, .pocketflow-message.bot h2, .pocketflow-message.bot h3 {
            color: var(--chatbot-foreground, hsl(222.2 84% 4.9%));
            margin-top: 1em;
            margin-bottom: 0.5em;
        }

        .pocketflow-message.bot h1:first-child, 
        .pocketflow-message.bot h2:first-child, 
        .pocketflow-message.bot h3:first-child {
            margin-top: 0;
        }

        .pocketflow-message.bot code {
            background-color: var(--chatbot-muted, hsl(210 40% 96.1%));
            border-radius: 4px;
            padding: 0.2em 0.4em;
            font-size: 85%;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
        }

        .pocketflow-message.bot pre {
            padding: 12px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: var(--chatbot-muted, hsl(210 40% 96.1%));
            border-radius: 0.5rem;
            border: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
            margin: 8px 0;
        }

        .pocketflow-message.bot pre code {
            padding: 0;
            margin: 0;
            background-color: transparent;
            border: none;
        }

        .pocketflow-mermaid-diagram {
            display: flex;
            justify-content: center;
            margin: 12px 0;
            padding: 8px;
            background-color: var(--chatbot-background, hsl(0 0% 100%));
            border-radius: 0.5rem;
            border: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
        }

        .pocketflow-mermaid-diagram svg {
            max-width: 100%;
            height: auto;
        }

        /* --- TYPING INDICATOR --- */
        .pocketflow-typing-indicator {
            display: none;
            align-items: center;
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
            font-size: 0.85em;
            margin-bottom: 12px;
            padding: 0 14px;
        }

        .pocketflow-typing-indicator.active {
            display: flex;
        }

        .pocketflow-typing-dots {
            display: inline-flex;
            margin-left: 8px;
        }

        .pocketflow-typing-dots span {
            height: 4px;
            width: 4px;
            background-color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: chatbot-typing 1.4s infinite ease-in-out;
        }

        .pocketflow-typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .pocketflow-typing-dots span:nth-child(2) { animation-delay: -0.16s; }

        /* --- CHAT INPUT --- */
        #pocketflow-chat-input-area {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background-color: var(--chatbot-card, hsl(0 0% 100%));
            border-top: 1px solid var(--chatbot-border, hsl(214.3 31.8% 91.4%));
        }

        #pocketflow-chat-input {
            flex-grow: 1;
            padding: 10px 14px !important;
            border: 1px solid var(--chatbot-input, hsl(214.3 31.8% 91.4%)) !important;
            border-radius: 1.5rem !important;
            background-color: var(--chatbot-background, hsl(0 0% 100%)) !important;
            color: var(--chatbot-foreground, hsl(222.2 84% 4.9%)) !important;
            font-size: 14px !important;
            margin-right: 10px;
            outline: none !important;
            transition: border-color 0.2s, box-shadow 0.2s;
            resize: none !important;
            min-height: 44px !important;
            max-height: 120px !important;
            overflow: hidden !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
            box-sizing: border-box !important;
            appearance: none !important;
            -webkit-appearance: none !important;
            -moz-appearance: none !important;
        }

        #pocketflow-chat-input::placeholder { 
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%)) !important; 
        }

        #pocketflow-chat-input:focus {
            border-color: var(--chatbot-ring, hsl(222.2 84% 4.9%)) !important;
            box-shadow: 0 0 0 2px var(--chatbot-background, hsl(0 0% 100%)), 0 0 0 4px var(--chatbot-ring, hsl(222.2 84% 4.9%)) !important;
        }

        .pocketflow-char-counter {
            font-size: 11px;
            color: var(--chatbot-muted-foreground, hsl(215.4 16.3% 46.9%));
            margin-right: 8px;
            min-width: 45px;
            text-align: right;
        }

        .pocketflow-char-counter.warning {
            color: #f59e0b;
        }

        .pocketflow-char-counter.error {
            color: #ef4444;
        }

        #pocketflow-chat-send-button {
            padding: 0;
            background-color: var(--chatbot-primary, hsl(222.2 47.4% 11.2%));
            color: var(--chatbot-primary-foreground, hsl(210 40% 98%));
            border: none;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: opacity 0.2s;
            flex-shrink: 0;
        }

        #pocketflow-chat-send-button:hover { 
            opacity: 0.8; 
        }

        #pocketflow-chat-send-button:disabled { 
            opacity: 0.5; 
            cursor: not-allowed; 
        }

        #pocketflow-chat-send-button svg { 
            width: 18px; 
            height: 18px; 
            fill: var(--chatbot-primary-foreground, hsl(210 40% 98%)); 
        }
    `;

  // Inject styles into document
  const styleElement = document.createElement("style");
  styleElement.textContent = chatbotStyles;
  document.head.appendChild(styleElement);

  // Load external resources
  const loadResource = (url, type = "script") => {
    const selector =
      type === "script" ? `script[src="${url}"]` : `link[href="${url}"]`;
    if (document.querySelector(selector)) return Promise.resolve();

    return new Promise((resolve) => {
      const element = document.createElement(
        type === "script" ? "script" : "link"
      );
      if (type === "script") {
        element.src = url;
      } else {
        element.rel = "stylesheet";
        element.href = url;
      }
      element.onload = resolve;
      element.onerror = () => {
        console.warn(`Failed to load ${type}: ${url}`);
        resolve(); // Continue anyway
      };
      document.head.appendChild(element);
    });
  };

  // Create chat HTML elements
  function createChatElements() {
    // Create chat icon
    const chatIcon = document.createElement("div");
    chatIcon.id = "pocketflow-chat-icon";
    chatIcon.innerHTML = `
            <svg class="light-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path></svg>
            <svg class="dark-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path></svg>
        `;

    // Create chat window
    const chatWindow = document.createElement("div");
    chatWindow.id = "pocketflow-chat-window";
    chatWindow.innerHTML = `
            <div id="pocketflow-chat-header">
                <button id="pocketflow-chat-maximize-button" class="pocketflow-chat-header-button" aria-label="Maximize chat">
                    <svg class="icon-maximize" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
                    <svg class="icon-minimize" style="display:none;" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/></svg>
                </button>
                <button id="pocketflow-chat-new-conversation-button" class="pocketflow-chat-header-button" aria-label="Start new conversation">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>
                </button>
                <span id="pocketflow-connection-status"></span>
                <span class="header-title" id="pocketflow-chat-title">${chatbotName}</span>
                <button id="pocketflow-chat-close-button" class="pocketflow-chat-header-button" aria-label="Close chat">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
            </div>
            
            <div id="pocketflow-chat-messages">
                <div class="pocketflow-context-banner" id="pocketflow-chat-context-banner">
                    <strong><a href="https://github.com/The-Pocket/PocketFlow-Tutorial-Website-Chatbot" target="_blank" style="color: var(--chatbot-primary); text-decoration: none;">This chatbot is open source</a></strong>
                </div>
                
                <div class="pocketflow-message bot">
                    <div id="pocketflow-chat-welcome-message">
                        Welcome! I'm here to help you with questions about the configured pages. What would you like to know?
                    </div>
                </div>
            </div>
            
            <div class="pocketflow-typing-indicator" id="pocketflow-typing-indicator">
                <span>Assistant is thinking</span>
                <div class="pocketflow-typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            
            <div id="pocketflow-chat-input-area">
                <textarea id="pocketflow-chat-input" placeholder="Ask a question..." rows="1" maxlength="1000"></textarea>
                <span id="pocketflow-char-counter" class="pocketflow-char-counter">0/1000</span>
                <button id="pocketflow-chat-send-button" aria-label="Send message">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
                    </svg>
                </button>
            </div>
        `;

    // Append elements to body
    document.body.appendChild(chatIcon);
    document.body.appendChild(chatWindow);

    // Setup theme detection and observer
    setupThemeObserver();
    updateChatbotTheme(currentTheme);

    return { chatIcon, chatWindow };
  }

  // Initialize libraries and create chatbot
  Promise.all([
    loadResource("https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"),
    loadResource(
      "https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"
    ),
    loadResource(
      "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
    ),
    loadResource(
      "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css",
      "css"
    ),
  ])
    .then(() => {
      console.log("Chatbot dependencies loaded successfully");

      // Initialize libraries
      if (window.mermaid) {
        try {
          window.mermaid.initialize({
            startOnLoad: false,
            theme: "default",
            securityLevel: "loose",
          });
          console.log("Mermaid initialized");
        } catch (error) {
          console.warn("Failed to initialize Mermaid:", error);
        }
      } else {
        console.warn("Mermaid library not available");
      }

      if (window.marked) {
        try {
          if (window.hljs) {
            window.marked.setOptions({
              highlight: function (code, lang) {
                if (lang && window.hljs.getLanguage(lang)) {
                  try {
                    return window.hljs.highlight(code, { language: lang })
                      .value;
                  } catch (err) {}
                }
                try {
                  return window.hljs.highlightAuto(code).value;
                } catch (err) {}
                return code;
              },
              langPrefix: "hljs language-",
            });
            console.log("Marked with highlight.js initialized");
          } else {
            console.warn("highlight.js not available, using basic marked");
          }
        } catch (error) {
          console.warn("Failed to initialize Marked:", error);
        }
      } else {
        console.warn("Marked library not available");
      }

      // Create chat elements
      const { chatIcon, chatWindow } = createChatElements();

      // Update welcome message with current URL
      const welcomeMessage = document.getElementById(
        "pocketflow-chat-welcome-message"
      );
      welcomeMessage.innerHTML = `Welcome! I'm here to help you with questions about: <a href="${finalCurrentUrl}" target="_blank" style="color: var(--chatbot-primary); text-decoration: none;">${finalCurrentUrl}</a>. What would you like to know?`;

      // Initialize chatbot functionality
      initializeChatbotLogic(
        finalCurrentUrl,
        extra_urls,
        prefixes,
        chatbotName,
        wsUrl,
        instruction,
        isOpen,
        wasCurrentUrlProvided
      );
    })
    .catch((error) => {
      console.error("Failed to load chatbot dependencies:", error);
      // Still try to create a basic chatbot without external libraries
      try {
        const { chatIcon, chatWindow } = createChatElements();
        const welcomeMessage = document.getElementById(
          "pocketflow-chat-welcome-message"
        );
        welcomeMessage.innerHTML = `Welcome! I'm here to help you with questions about: <a href="${finalCurrentUrl}" target="_blank" style="color: var(--chatbot-primary); text-decoration: none;">${finalCurrentUrl}</a>. What would you like to know?`;

        initializeChatbotLogic(
          finalCurrentUrl,
          extra_urls,
          prefixes,
          chatbotName,
          wsUrl,
          instruction,
          isOpen,
          wasCurrentUrlProvided
        );
      } catch (fallbackError) {
        console.error("Failed to create fallback chatbot:", fallbackError);
      }
    });

  function initializeChatbotLogic(
    currentUrl,
    extraUrls,
    prefixes,
    chatbotName,
    wsUrl,
    instruction = "",
    isOpenByDefault = false,
    wasCurrentUrlProvided = false
  ) {
    // Get chat elements
    const chatIcon = document.getElementById("pocketflow-chat-icon");
    const chatWindow = document.getElementById("pocketflow-chat-window");
    const chatMessages = document.getElementById("pocketflow-chat-messages");
    const chatInput = document.getElementById("pocketflow-chat-input");
    const sendButton = document.getElementById("pocketflow-chat-send-button");
    const closeButton = document.getElementById("pocketflow-chat-close-button");
    const maximizeButton = document.getElementById(
      "pocketflow-chat-maximize-button"
    );
    const newConversationButton = document.getElementById(
      "pocketflow-chat-new-conversation-button"
    );
    const typingIndicator = document.getElementById(
      "pocketflow-typing-indicator"
    );
    const charCounter = document.getElementById("pocketflow-char-counter");
    const connectionStatus = document.getElementById(
      "pocketflow-connection-status"
    );

    // Chat state variables
    let isChatOpen = isOpenByDefault; // Open by default if specified
    let isChatMaximized = false; // Never start maximized, let user choose
    let socket = null;
    let isFirstMessage = true;
    let hasPageChanged = false; // Track if page changed since last conversation

    // Set initial state if opened by default
    if (isOpenByDefault) {
      isChatMaximized = true;
      chatWindow.classList.add("open", "maximized");

      const [iconMax, iconMin] = ["icon-maximize", "icon-minimize"].map((cls) =>
        maximizeButton.querySelector(`.${cls}`)
      );
      iconMax.style.display = "none";
      iconMin.style.display = "block";
      maximizeButton.setAttribute("aria-label", "Restore chat");
    }

    // Auto-resize textarea and update character counter
    chatInput.addEventListener("input", () => {
      chatInput.style.height = "auto";
      const newHeight = Math.min(chatInput.scrollHeight, 120);
      chatInput.style.height = newHeight + "px";

      // Ensure overflow is always hidden to prevent scrollbars
      chatInput.style.overflow = "hidden";

      const currentLength = chatInput.value.length;
      charCounter.textContent = `${currentLength}/1000`;

      charCounter.classList.remove("warning", "error");
      if (currentLength > 900) {
        charCounter.classList.add("error");
      } else if (currentLength > 800) {
        charCounter.classList.add("warning");
      }

      if (!chatInput.disabled) {
        sendButton.disabled = currentLength > 1000 || currentLength === 0;
      }
    });

    // Connection status management
    function setStatus(status) {
      // 'connecting', 'connected', 'disconnected'
      if (connectionStatus) {
        connectionStatus.className = `pocketflow-status-${status}`;
      }
    }

    // Chat window toggle functionality
    function toggleChat(forceOpen = null) {
      isChatOpen = forceOpen !== null ? forceOpen : !isChatOpen;
      chatWindow.classList.toggle("open", isChatOpen);
      if (isChatOpen) {
        chatInput.focus();
        connectWebSocket();
      } else {
        // When closing, also un-maximize and reset state
        if (isChatMaximized) {
          isChatMaximized = false;
          chatWindow.classList.remove("maximized");
          const iconMax = maximizeButton.querySelector(".icon-maximize");
          const iconMin = maximizeButton.querySelector(".icon-minimize");
          iconMax.style.display = "block";
          iconMin.style.display = "none";
          maximizeButton.setAttribute("aria-label", "Maximize chat");
        }
        // Keep WebSocket connection alive when closing UI
        // User can continue their session when reopening
      }
    }

    // Chat window maximize/minimize functionality
    function toggleMaximize() {
      isChatMaximized = !isChatMaximized;
      chatWindow.classList.toggle("maximized", isChatMaximized);
      const iconMax = maximizeButton.querySelector(".icon-maximize");
      const iconMin = maximizeButton.querySelector(".icon-minimize");
      iconMax.style.display = isChatMaximized ? "none" : "block";
      iconMin.style.display = isChatMaximized ? "block" : "none";
      maximizeButton.setAttribute(
        "aria-label",
        isChatMaximized ? "Restore chat" : "Maximize chat"
      );
    }

    // Function to render markdown with mermaid diagrams
    async function renderMarkdownWithMermaid(markdownText) {
      // If no markdown library available, return plain text
      if (!window.marked) {
        console.warn("Marked library not available, returning plain text");
        return markdownText.replace(/\n/g, "<br>");
      }

      try {
        let html = window.marked.parse(markdownText);

        // Only try mermaid if library is available
        if (window.mermaid) {
          const tempDiv = document.createElement("div");
          tempDiv.innerHTML = html;

          const mermaidBlocks = tempDiv.querySelectorAll(
            "code.language-mermaid"
          );
          for (let i = 0; i < mermaidBlocks.length; i++) {
            const block = mermaidBlocks[i];
            const mermaidCode = block.textContent;

            try {
              const diagramId = `mermaid-diagram-${Date.now()}-${i}`;
              const { svg } = await window.mermaid.render(
                diagramId,
                mermaidCode
              );

              const svgContainer = document.createElement("div");
              svgContainer.className = "pocketflow-mermaid-diagram";
              svgContainer.innerHTML = svg;

              const preElement = block.closest("pre");
              if (preElement) {
                preElement.parentNode.replaceChild(svgContainer, preElement);
              }
            } catch (error) {
              console.error("Mermaid rendering error:", error);
              block.textContent = `Error rendering diagram: ${error.message}\n\n${mermaidCode}`;
            }
          }

          return tempDiv.innerHTML;
        }

        return html;
      } catch (error) {
        console.error("Markdown rendering error:", error);
        return markdownText.replace(/\n/g, "<br>");
      }
    }

    // Message management functions
    function addMessage(content, isUser = false, isSystem = false) {
      const messageElement = document.createElement("div");
      if (isSystem) {
        messageElement.classList.add("pocketflow-message", "system");
      } else {
        messageElement.classList.add(
          "pocketflow-message",
          isUser ? "user" : "bot"
        );
      }
      messageElement.innerHTML = content;

      chatMessages.appendChild(messageElement);
      const clearDiv = document.createElement("div");
      clearDiv.style.clear = "both";
      chatMessages.appendChild(clearDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping() {
      typingIndicator.classList.add("active");
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideTyping() {
      typingIndicator.classList.remove("active");
    }

    function clearChatHistory() {
      // Keep only the context banner and welcome message
      const contextBanner = document.getElementById(
        "pocketflow-chat-context-banner"
      );
      const welcomeMessage = document.querySelector(".pocketflow-message.bot");

      chatMessages.innerHTML = "";
      if (contextBanner) chatMessages.appendChild(contextBanner);
      if (welcomeMessage) chatMessages.appendChild(welcomeMessage);

      const clearDiv = document.createElement("div");
      clearDiv.style.clear = "both";
      chatMessages.appendChild(clearDiv);
    }

    function startNewConversation() {
      // Close existing WebSocket connection if any
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }

      // Clear chat history
      clearChatHistory();

      // Reset conversation state
      isFirstMessage = true;
      hasPageChanged = false;

      // Hide typing indicator
      hideTyping();

      // Re-enable input
      chatInput.disabled = false;
      sendButton.disabled = chatInput.value.trim().length === 0;

      // Add system message to indicate new conversation started
      addMessage("New conversation started!", false, true);

      // Focus on input
      chatInput.focus();

      // Reset connection status
      setStatus("disconnected");
    }

    // WebSocket connection management
    function connectWebSocket() {
      if (socket && socket.readyState === WebSocket.OPEN) return;

      setStatus("connecting");
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log("WebSocket connected");
        setStatus("connected");
      };

      socket.onclose = () => {
        console.log("WebSocket disconnected");
        setStatus("disconnected");
        hideTyping();
        addMessage(
          "Connection lost. Your next message will start a new conversation.",
          false,
          true
        );
        isFirstMessage = true;
        socket = null;

        chatInput.disabled = false;
        sendButton.disabled = chatInput.value.trim().length === 0;
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        setStatus("disconnected");
        addMessage("A connection error occurred. Please refresh.", false, true);
      };

      socket.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        const enableInput = () => {
          chatInput.disabled = false;
          sendButton.disabled = chatInput.value.trim().length === 0;
          chatInput.focus();
        };

        switch (data.type) {
          case "final_answer":
            hideTyping();
            const renderedHTML = await renderMarkdownWithMermaid(
              data.payload.trim()
            );
            addMessage(renderedHTML, false);

            if (data.useful_pages?.length > 0) {
              const pagesHTML =
                "<strong>You may find these pages useful:</strong><ul>" +
                data.useful_pages
                  .map(
                    (p) =>
                      `<li><a href="${p}" target="_blank" style="color: var(--chatbot-primary); text-decoration: none;">${p}</a></li>`
                  )
                  .join("") +
                "</ul>";
              addMessage(pagesHTML, false);
            }
            enableInput();
            break;

          case "error":
            hideTyping();
            addMessage(`Sorry, an error occurred: ${data.payload}`, false);
            enableInput();
            break;

          case "progress":
            hideTyping();
            addMessage(data.payload, false);
            showTyping();
            break;
        }
      };
    }

    // Message sending functionality
    async function sendMessage() {
      const message = chatInput.value.trim();
      if (!message || sendButton.disabled || message.length > 1000) {
        if (message.length > 1000)
          alert("Message is too long. Please keep it under 1000 characters.");
        return;
      }

      // Handle page change scenario
      if (hasPageChanged) {
        // Clear history when starting new conversation after page change
        clearChatHistory();
        hasPageChanged = false;
      } else if (isFirstMessage && chatMessages.children.length > 3) {
        // Clear history if needed for regular first message
        clearChatHistory();
      }

      // Update UI
      addMessage(message, true);
      chatInput.value = "";
      chatInput.style.height = "auto";
      chatInput.dispatchEvent(new Event("input"));

      [sendButton, chatInput].forEach((el) => (el.disabled = true));
      showTyping();
      connectWebSocket();

      // Prepare message data
      const messageData = {
        type: isFirstMessage ? "start" : "follow_up",
        payload: {
          question: message,
          ...(isFirstMessage && {
            current_url: wasCurrentUrlProvided
              ? currentUrl
              : window.location.href,
            extra_urls: wasCurrentUrlProvided ? extraUrls : [],
            prefixes,
            instruction,
          }),
        },
      };

      // Wait for connection and send
      const waitForConnection = () => {
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify(messageData));
          if (isFirstMessage) isFirstMessage = false;
        } else {
          setTimeout(waitForConnection, 5);
        }
      };
      waitForConnection();
    }

    // Event listeners for chat functionality
    chatIcon.addEventListener("click", () => toggleChat(true));
    closeButton.addEventListener("click", () => toggleChat(false));
    maximizeButton.addEventListener("click", toggleMaximize);
    newConversationButton.addEventListener("click", startNewConversation);
    sendButton.addEventListener("click", sendMessage);

    chatInput.addEventListener("keypress", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    // Initialize character counter
    chatInput.dispatchEvent(new Event("input"));

    // Connect WebSocket and focus input if opened by default
    if (isOpenByDefault) {
      connectWebSocket();
      chatInput.focus();
    }

    // Function to handle page change
    function handlePageChange(newUrl) {
      // Update welcome message
      const welcomeMessage = document.getElementById(
        "pocketflow-chat-welcome-message"
      );
      if (welcomeMessage) {
        welcomeMessage.innerHTML = `Welcome! I'm here to help you with questions about: <a href="${newUrl}" target="_blank" style="color: var(--chatbot-primary); text-decoration: none;">${newUrl}</a>. What would you like to know?`;
      }

      // Check if there's existing chat history (more than just welcome messages)
      const hasExistingHistory = chatMessages.children.length > 3; // context banner + welcome + clear div

      if (hasExistingHistory) {
        // Don't clear history immediately, just add a system message and close WebSocket
        addMessage(
          `Page changed to: ${newUrl}. Your next message will start a new conversation for this page.`,
          false,
          true
        );

        // Close WebSocket but don't clear history yet
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.close();
        }

        // Mark that page has changed
        hasPageChanged = true;
        isFirstMessage = true; // Next message will be treated as first message
      } else {
        // No significant history, just update welcome message (already done above)
        hasPageChanged = false;
      }
    }

    // Set up automatic URL change detection for SPAs (only if current_url wasn't explicitly provided)
    if (!wasCurrentUrlProvided) {
      setupAutomaticUrlDetection(handlePageChange);
    }
  }
}

// Set up URL change detection for SPAs
function setupAutomaticUrlDetection(onPageChangeCallback) {
  let currentUrl = window.location.href;

  const handleUrlChange = () => {
    const newUrl = window.location.href;
    if (newUrl === currentUrl) return;

    currentUrl = newUrl;

    // Call the callback to handle page change
    if (onPageChangeCallback) {
      onPageChangeCallback(newUrl);
    }
  };

  // Monitor navigation
  ["pushState", "replaceState"].forEach((method) => {
    const original = history[method];
    history[method] = function (...args) {
      original.apply(history, args);
      setTimeout(handleUrlChange, 0);
    };
  });

  ["popstate", "hashchange"].forEach((event) => {
    window.addEventListener(event, handleUrlChange);
  });
}

// Make the function available globally
window.initializeChatbot = initializeChatbot;
