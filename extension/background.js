let capturedUrls = {};

// Escuta todas as requisições de rede antes de acontecerem
chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
        // Ignora requisições de background sem aba definida
        if (details.tabId === -1) return;

        const url = details.url;

        // Se a requisição for de um arquivo de vídeo ou playlist HLS (m3u8)
        if (url.includes('.m3u8') || url.includes('.mp4')) {
            if (!capturedUrls[details.tabId]) {
                capturedUrls[details.tabId] = new Set();
            }
            capturedUrls[details.tabId].add(url);
        }
    },
    { urls: ["<all_urls>"] }
);

// Limpa a memória quando você atualiza a página
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.status === 'loading') {
        capturedUrls[tabId] = new Set();
    }
});

// Envia as URLs capturadas para o popup quando ele pedir
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getNetworkVideos") {
        const urls = capturedUrls[request.tabId] ? Array.from(capturedUrls[request.tabId]) : [];
        sendResponse({ urls: urls });
    }
});