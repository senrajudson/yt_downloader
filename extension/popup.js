//popup.js

let foundVideos = [];

// Ao abrir, manda o radar escanear a página
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const currentTab = tabs[0];

  // ==========================================
  // 0. A URL da própria página (A melhor amiga do yt-dlp)
  // ==========================================
  let mainPageVideo = {
    url: currentTab.url,
    title: currentTab.title + ' (Link Principal da Página)',
  };

  // 1. Pergunta pro content.js (Lê o HTML - Bom para Iframes)
  chrome.tabs.sendMessage(
    currentTab.id,
    { action: 'scanVideos' },
    (domResponse) => {
      let domVideos =
        domResponse && domResponse.videos ? domResponse.videos : [];

      // 2. Pergunta pro background.js (Lê a Rede - Bom pra Blobs)
      chrome.runtime.sendMessage(
        { action: 'getNetworkVideos', tabId: currentTab.id },
        (netResponse) => {
          let networkUrls =
            netResponse && netResponse.urls ? netResponse.urls : [];

          // Transforma as URLs da rede no formato de objeto com Título
          let networkVideos = networkUrls.map((url) => ({
            url: url,
            title: currentTab.title,
          }));

          // 3. Junta tudo: A página + os do HTML + os da Rede
          let allVideos = [mainPageVideo, ...domVideos, ...networkVideos];

          // Remove duplicatas baseando-se na URL
          foundVideos = Array.from(
            new Map(allVideos.map((v) => [v.url, v])).values()
          );

          // 4. Mostra na tela
          if (foundVideos.length > 0) {
            let htmlText = `<strong>${foundVideos.length} link(s) enviado(s) para o yt-dlp:</strong><br><br>`;
            foundVideos.forEach((v) => {
              htmlText += `<small>- ${v.title}</small><br>`;
            });
            document.getElementById('count').innerHTML = htmlText;
          } else {
            document.getElementById('count').innerHTML =
              'Dê o <b>Play</b> no vídeo e reabra este menu!';
          }
        }
      );
    }
  );
});

document.getElementById('download-all').addEventListener('click', async () => {
  if (foundVideos.length === 0) {
    alert('Não há vídeos para baixar!');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const domain = new URL(tab.url).hostname;
  const cookies = await chrome.cookies.getAll({ domain: domain });

  document.getElementById('download-all').innerText = 'Enviando para API...';

  try {
    const response = await fetch('http://127.0.0.1:8000/download_smart_batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        videos: foundVideos,
        cookies: cookies,
      }),
    });

    const result = await response.json();
    console.log(result.message);
    document.getElementById('download-all').innerText = 'Sucesso! Baixando...';
  } catch (error) {
    console.error('Erro:', error);
    document.getElementById('download-all').innerText = 'Erro na API!';
  }
});
