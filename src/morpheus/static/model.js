// model.js linked in html <script>

let history = [];
const inputField = document.getElementById('userInput');
const sendBtn = document.querySelector('button');
const terminal = document.getElementById('terminal');

let lastMessageId = 1;

async function sendMessage() {
    const text = inputField.value;
    if(!text) return;

    // 1. UI State: Disable input and button while Helios thinks
    inputField.disabled = true;
    sendBtn.disabled = true;
    sendBtn.innerText = "ANALYZING...";

    terminal.innerHTML += `<div style="color: #fff; margin-top: 10px;"><strong style="color: #00ff41;">USER:</strong> ${text}</div>`;
    inputField.value = '';

    // history.push({role: "user", content: text});

    // 1. Create a new div for Morpheus's response immediately
    const containerResponse = document.createElement('div');
    containerResponse.setAttribute('id', ++lastMessageId);
    containerResponse.style.marginBottom = "15px";
    containerResponse.style.whiteSpace = "pre-wrap";

    // const bufferAnalysis = document.createElement('div');
    // bufferAnalysis.setAttribute('id', 'analysis');

    const bufferResponse = document.createElement('div');
    bufferResponse.setAttribute('id', 'response');
    
    // containerResponse.appendChild(bufferAnalysis);
    containerResponse.appendChild(bufferResponse);
    terminal.appendChild(containerResponse);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: text})
        });


        // 2. Read the stream chunk by chunk
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        // let cachedResponse = "";

        // let isThinking = false;
        // let isResponding = false;
        // let audioPlayed = false;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            let chunk = decoder.decode(value, { stream: true });
            if (bufferResponse.innerHTML === "") {
                bufferResponse.innerHTML = `<strong style="color: #00ff41;">MORPHEUS:</strong> `;
            }
            bufferResponse.innerHTML += chunk;
            // --- NEW: INTERCEPT AUDIO TAG ---
            // if (!audioPlayed && chunk.includes('[AUDIO_READY]:')) {
            //     const parts = chunk.split('[AUDIO_READY]:');
                
            //     // 1. Extract the URL and play it
            //     const audioUrl = parts[1].trim();
            //     if (audioUrl) {
            //         console.log("Playing Morpheus Voice:", audioUrl);
            //         const audio = new Audio(audioUrl);
            //         audio.play().catch(e => console.error("Playback blocked by browser:", e));
            //         audioPlayed = true; 
            //     }
                
            // } else {

            //     if (bufferResponse.innerHTML === "") {
            //         bufferResponse.innerHTML = `<strong style="color: #00ff41;">MORPHEUS:</strong> `;
            //     }
            //     bufferResponse.innerHTML += chunk;
            // }

            // if (!isThinking && cachedResponse.includes('[THINKING]')) {
            //     isThinking = true;
            // } else if (!isResponding && cachedResponse.includes('[RESPONSE]')) {
            //     isResponding = true;
            //     containerResponse.querySelector('#analysis').remove();
            //     bufferResponse.innerHTML = `<strong style="color: #00ff41;">MORPHEUS:</strong> `;
            //     chunk = chunk.replace('[RESPONSE]', '');
            // }


            // if (isResponding) {
            //     bufferResponse.innerHTML += chunk;
            // } else if (isThinking) {
            //     bufferAnalysis.innerHTML += chunk;
            // } else if (!audioPlayed) {
            //     bufferResponse.innerHTML += chunk;
            // }

            // terminal.scrollTop = terminal.scrollHeight;
        }

        // history.push({role: "morpheus", content: cachedResponse});

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

            // const lastMessageText = document.getElementById(lastMessageId).innerHTML;
            // console.log(lastMessageText);
            const audio = new Audio();

            // 2. Set the source directly to your server endpoint
            // If your backend endpoint takes a POST request, skip to Option 2.
            // If you can modify your backend to accept a query string (GET), use this:
            audio.src = `http://localhost:8000/speak-last-message`;

            // 3. Play immediately (the browser will buffer the incoming chunks)
            audio.play()
                .then(() => console.log("Audio streaming started successfully!"))
                .catch(error => console.error("Playback failed:", error));            

        });
    }
});
