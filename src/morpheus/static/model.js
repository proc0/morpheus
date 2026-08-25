// model.js linked in html <script>

const inputField = document.getElementById('userInput');
const sendBtn = document.querySelector('button');
const terminal = document.getElementById('terminal');

const LOADING = '[Thinking...]';
const MORPHEUS_NAME = "[Morpheus]";
const HUMAN_NAME = "[Human]";

async function sendMessage() {
    const text = inputField.value;
    if(!text) return;

    inputField.disabled = true;
    inputField.value = '';
    sendBtn.disabled = true;

    terminal.querySelectorAll('article').forEach((a) => a.remove());

    const userPrompt = document.getElementById('comment').content.cloneNode(true);
    userPrompt.querySelector('label').innerHTML = HUMAN_NAME;
    userPrompt.querySelector('content').innerHTML = text;
    terminal.append(userPrompt);

    const morpheusResponse = document.getElementById('comment').content.cloneNode(true);
    const morpheusName = morpheusResponse.querySelector('label');
    const bufferResponse = morpheusResponse.querySelector('content');
    morpheusResponse.querySelector('article').setAttribute('id', 'morpheus-response');
    morpheusResponse.querySelector('article').classList.add('hide');
    morpheusName.innerHTML = MORPHEUS_NAME;
    terminal.append(morpheusResponse);

    const loader = document.createElement('span');
    loader.setAttribute('id', 'loader');
    loader.innerHTML = LOADING;
    terminal.append(loader);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: text})
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            bufferResponse.innerHTML += chunk;
        }
    } catch (error) {
        terminal.innerHTML += `<div style="color: red;">[SYSTEM ERROR]</div>`;
        console.log(error);
    }

}

inputField.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage().finally(() => {
            inputField.disabled = false;
            sendBtn.disabled = false;
            inputField.focus();

            const audio = new Audio();
            audio.src = `http://localhost:8000/speak-last-message`;
            audio.play()
                .then(() => {
                    document.getElementById('loader').remove();
                    document.getElementById('morpheus-response').classList.remove('hide')
                })
                .catch(error => console.error("Morpheus Speak failed:", error));            

        });
    }
});
