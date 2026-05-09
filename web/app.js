const DOM = {
  chatWrapper: document.querySelector(".chat-wrapper"), 
  chatContainer: document.getElementById("chat-container"),
  chatInner: document.querySelector(".chat-inner"),
  pdfInput: document.getElementById("pdfInput"),
  fileNameDiv: document.getElementById("fileName"),
  dropZone: document.getElementById("dropZone"),
  progressBar: document.getElementById("progressBar"),
  progressContainer: document.getElementById("progressContainer"),
  inputField: document.getElementById("input"),
  submitBtn: document.querySelector(".send-btn")
};

const state = {
  selectedFile: null,
  isGenerating: false,
  isUploading: false,
  history: [] 
};

// Configure marked.js to use Prism for code blocks safely
marked.setOptions({
  highlight: function(code, lang) {
    if (Prism.languages[lang]) {
      return Prism.highlight(code, Prism.languages[lang], lang);
    } else {
      return code;
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  appendMessage("System Online. Awaiting queries.", "ai");
});

window.handleSend = async function(event) {
  event.preventDefault(); 
  const text = DOM.inputField.value.trim();
  if (!text || state.isGenerating) return;

  appendMessage(text, "user");
  DOM.inputField.value = "";
  await fetchStreamedResponse(text);
};

function appendMessage(text, sender) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}`;
  // Using DOMPurify to prevent XSS attacks if handling raw HTML docs
  msgDiv.innerHTML = DOMPurify.sanitize(marked.parse(text));
  DOM.chatInner.appendChild(msgDiv);
  scrollToBottom();
  return msgDiv;
}

async function fetchStreamedResponse(userText) {
  state.isGenerating = true;
  DOM.inputField.disabled = true;
  DOM.submitBtn.style.opacity = "0.5";

  const aiMsgDiv = document.createElement("div");
  aiMsgDiv.className = "message ai";
  aiMsgDiv.innerHTML = "<span style='color: var(--neon-cyan); font-family: Rajdhani;'>PROCESSING...</span>";
  DOM.chatInner.appendChild(aiMsgDiv);
  scrollToBottom();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        message: userText,
        history: state.history
      })
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let fullResponse = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      fullResponse += decoder.decode(value, { stream: true });
      aiMsgDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullResponse));
      scrollToBottom();
    }

    state.history.push({ role: "user", content: userText });
    state.history.push({ role: "assistant", content: fullResponse });

  } catch (error) {
    console.error("Chat Stream Error:", error);
    aiMsgDiv.innerHTML = `<span style="color: var(--neon-orange);">CONNECTION FAILED.</span>`;
  } finally {
    state.isGenerating = false;
    DOM.inputField.disabled = false;
    DOM.submitBtn.style.opacity = "1";
    DOM.inputField.focus();
  }
}

window.createNewChat = function() {
  if (state.isGenerating) return;
  DOM.chatInner.innerHTML = "";
  state.history = []; 
  appendMessage("Session cleared. Ready.", "ai");
};

function scrollToBottom() {
  requestAnimationFrame(() => {
    DOM.chatWrapper.scrollTop = DOM.chatWrapper.scrollHeight;
  });
}

// FILE UPLOAD 
function processFileSelection(file) {
  if (!file) return;
  if (file.type !== "application/pdf") {
    alert("Invalid format. PDF required.");
    return;
  }
  state.selectedFile = file;
  DOM.fileNameDiv.innerText = file.name;
}

DOM.pdfInput.addEventListener("change", (e) => processFileSelection(e.target.files[0]));

DOM.dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  DOM.dropZone.classList.add("dragover"); 
});

DOM.dropZone.addEventListener("dragleave", (e) => {
  e.preventDefault();
  DOM.dropZone.classList.remove("dragover");
});

DOM.dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  DOM.dropZone.classList.remove("dragover");
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    processFileSelection(e.dataTransfer.files[0]);
  }
});

window.uploadPDF = function() {
  if (!state.selectedFile) return alert("Select payload first.");
  if (state.isUploading) return;

  state.isUploading = true;
  DOM.progressContainer.style.display = "block";
  DOM.progressBar.style.width = "0%";

  const formData = new FormData();
  formData.append("file", state.selectedFile);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload");

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percentComplete = (e.loaded / e.total) * 100;
      DOM.progressBar.style.width = percentComplete + "%";
    }
  };

  xhr.onload = () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      alert("Data link established.");
      resetUploadUI(true);
    } else {
      alert("Transfer failed: " + xhr.status);
      resetUploadUI(false);
    }
  };

  xhr.onerror = () => {
    alert("Network error.");
    resetUploadUI(false);
  };

  xhr.send(formData);
};

function resetUploadUI(success) {
  state.isUploading = false;
  if (success) {
    state.selectedFile = null;
    DOM.fileNameDiv.innerText = "No file selected";
    DOM.pdfInput.value = ""; 
  }
  setTimeout(() => {
    DOM.progressContainer.style.display = "none";
    DOM.progressBar.style.width = "0%";
  }, 1500);
}