//background.js

let capturedUrls = {};

// Escuta todas as requisições de rede antes de acontecerem
chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
        // Ignora requisições de background sem aba definida
        if (details.tabId === -1) return;

        try {
            const urlObj = new URL(details.url);
            
            // Verifica o caminho final (pathname), ignorando tudo que vem depois do "?"
            if (urlObj.pathname.endsWith('.m3u8') || urlObj.pathname.endsWith('.mp4')) {
                if (!capturedUrls[details.tabId]) {
                    capturedUrls[details.tabId] = new Set();
                }
                // Adiciona a URL completa capturada
                capturedUrls[details.tabId].add(details.url);
            }
        } catch (error) {
            // Ignora URLs malformadas que possam quebrar a classe new URL()
            console.error("Erro ao analisar URL na rede:", error);
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
    // Retorna true para manter o canal de mensagem aberto (boa prática)
    return true; 
});