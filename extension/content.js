// Função auxiliar para caçar o título subindo pelas divs
function extractTitle(element) {
    let currentEl = element;
    for (let i = 0; i < 6; i++) {
        if (!currentEl) break;
        const heading = currentEl.querySelector('h1, h2, h3, [class*="title"], [class*="titulo"]');
        if (heading && heading.innerText.trim() !== '') {
            return heading.innerText.trim();
        }
        currentEl = currentEl.parentElement;
    }
    return document.title || "Aula_Sem_Titulo";
}

function scanPageForVideos() {
    let results = [];

    // ==========================================
    // CASO 1: YOUTUBE NATIVO
    // ==========================================
    if (window.location.hostname.includes('youtube.com') && window.location.pathname === '/watch') {
        results.push({
            url: window.location.href, // Manda a URL da página pro yt-dlp resolver
            title: document.title.replace(/^\(\d+\)\s/, '').replace(' - YouTube', '') // Limpa notificações do título
        });
    }

    // ==========================================
    // CASO 2: IFRAMES (FIAP Embed, Vimeo, etc)
    // ==========================================
    // Como o CORS bloqueia ler a tag <video> lá dentro, mandamos o link do iframe pro yt-dlp!
    document.querySelectorAll('iframe').forEach(ifr => {
        if (ifr.src && (ifr.src.includes('embed') || ifr.src.includes('video') || ifr.src.includes('player'))) {
            results.push({
                url: ifr.src,
                title: ifr.title || extractTitle(ifr)
            });
        }
    });

    // ==========================================
    // CASO 3: TAGS DE VÍDEO PADRÃO E M3U8
    // ==========================================
    document.querySelectorAll('video').forEach(vid => {
        let url = null;

        // Procura link .m3u8 nos atributos da própria tag ou nas divs pai
        let currentEl = vid;
        for (let i = 0; i < 5; i++) {
            if (!currentEl) break;
            for (let attr of currentEl.attributes) {
                let unescapedValue = attr.value.replace(/\\\//g, '/'); 
                let m3u8Match = unescapedValue.match(/https?:\/\/[^"'\s]+\.m3u8/);
                if (m3u8Match) {
                    url = m3u8Match[0];
                    break;
                }
            }
            if (url) break;
            currentEl = currentEl.parentElement;
        }

        // Se for um vídeo normal solto (ignorando blobs)
        if (!url && vid.src && !vid.src.startsWith('blob:')) {
            url = vid.src;
        }

        if (url) {
            results.push({ url: url, title: extractTitle(vid) });
        }
    });

    // ==========================================
    // FILTRO DE DUPLICATAS
    // ==========================================
    const uniqueResults = Array.from(new Map(results.map(item => [item.url, item])).values());
    return uniqueResults;
}

// Escuta o chamado do popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scanVideos") {
        sendResponse({ videos: scanPageForVideos() });
    }
});