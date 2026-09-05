const chat = document.getElementById("chat");
const userInput = document.getElementById("userInput");
const sendButton = document.getElementById("sendButton");

function addMessage(text, className) {
	const message = document.createElement("div");
	message.className = `message ${className}`;
	message.textContent = text;
	chat.appendChild(message);
	chat.scrollTop = chat.scrollHeight;
	return message;
}

function speakReply(text) {
	if (!("speechSynthesis" in window)) {
		return;
	}

	window.speechSynthesis.cancel();
	const utterance = new SpeechSynthesisUtterance(text);
	utterance.pitch = 1.5;
	utterance.rate = 0.85;
	utterance.volume = 0.9;
	window.speechSynthesis.speak(utterance);
}

async function sendMessage() {
	const message = userInput.value.trim();
	if (!message || sendButton.disabled) {
		return;
	}

	addMessage(message, "user-message");
	userInput.value = "";
	userInput.disabled = true;
	sendButton.disabled = true;
	sendButton.textContent = "Thinking...";
	const loadingMessage = addMessage("Mrow...", "bot-message");
	let reply = "";
	let translationElement;

	try {
		const response = await fetch("/chat/stream", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ message }),
		});
		if (!response.ok) {
			const data = await response.json();
			throw new Error(data.detail || "The cat is unavailable.");
		}

		if (!response.body) {
			throw new Error("Streaming is not supported by this browser.");
		}

		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		let buffer = "";

		while (true) {
			const { value, done } = await reader.read();
			buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
			const events = buffer.split("\n\n");
			buffer = events.pop();

			for (const event of events) {
				const eventType = event.match(/^event: (.+)$/m)?.[1];
				const dataLine = event.match(/^data: (.+)$/m)?.[1];
				if (!eventType || !dataLine) {
					continue;
				}

				const data = JSON.parse(dataLine);
				if (eventType === "chunk") {
					reply += data.text;
					loadingMessage.textContent = reply;
				} else if (eventType === "translation") {
					translationElement = document.createElement("div");
					translationElement.className = "translation";
					translationElement.textContent = `Translation: ${data.text}`;
					chat.insertBefore(translationElement, loadingMessage.nextSibling);
				} else if (eventType === "error") {
					throw new Error(data.detail);
				}
			}

			if (done) {
				break;
			}
		}

		speakReply(reply);
	} catch (error) {
		loadingMessage.textContent = `HISS! ${error.message}`;
	} finally {
		userInput.disabled = false;
		sendButton.disabled = false;
		sendButton.textContent = "Send";
		userInput.focus();
	}
}

sendButton.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (event) => {
	if (event.key === "Enter") {
		sendMessage();
	}
});
