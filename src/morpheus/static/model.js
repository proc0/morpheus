// model.js linked in html <script>

let history = [];
const inputField = document.getElementById('userInput');
const sendBtn = document.querySelector('button');
const terminal = document.getElementById('terminal');

async function sendMessage() {
    const text = inputField.value;
    if(!text) return;

    // 1. UI State: Disable input and button while Helios thinks
    inputField.disabled = true;
    sendBtn.disabled = true;
    sendBtn.innerText = "ANALYZING...";

    terminal.innerHTML += `<div style="color: #fff; margin-top: 10px;"><strong style="color: #00ff41;">USER:</strong> ${text}</div>`;
    inputField.value = '';

    history.push({role: "user", content: text});

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: text})
        });

        // 1. Create a new div for Morpheus's response immediately
        const containerResponse = document.createElement('div');
        containerResponse.style.marginBottom = "15px";
        containerResponse.style.whiteSpace = "pre-wrap";

        const bufferAnalysis = document.createElement('div');
        bufferAnalysis.setAttribute('id', 'analysis');

        const bufferResponse = document.createElement('div');
        bufferResponse.setAttribute('id', 'response');
        
        containerResponse.appendChild(bufferAnalysis);
        containerResponse.appendChild(bufferResponse);
        terminal.appendChild(containerResponse);

        // 2. Read the stream chunk by chunk
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let cachedResponse = "";

        let isThinking = false;
        let isResponding = false;
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            let chunk = decoder.decode(value, { stream: true });
            cachedResponse += chunk;
            
            // Append the chunk to the div in real-time
            if (!isThinking && cachedResponse.includes('[THINKING]')) {
                isThinking = true;
            } else if (!isResponding && cachedResponse.includes('[RESPONSE]')) {
                isResponding = true;
                containerResponse.querySelector('#analysis').remove();
                bufferResponse.innerHTML = `<strong style="color: #00ff41;">MORPHEUS:</strong> `;
                chunk = chunk.replace('[RESPONSE]', '');
            }


            if (isResponding) {
                bufferResponse.innerHTML += chunk;
            } else if (isThinking) {
                bufferAnalysis.innerHTML += chunk;
            } else {
                bufferResponse.innerHTML += chunk;
            }


            if (cachedResponse.includes('[AUDIO_READY]')) {
                console.log("AUDIO READY!!!!");
            }

            // terminal.scrollTop = terminal.scrollHeight;
        }

        history.push({role: "morpheus", content: cachedResponse});

    } catch (error) {
        terminal.innerHTML += `<div style="color: red;">[SYSTEM ERROR]</div>`;
    }

}

// --- THE ENTER KEY LOGIC ---
inputField.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage().finally(() => {
            inputField.disabled = false;
            sendBtn.disabled = false;
            sendBtn.innerText = "SEND";

        });
    }
});
