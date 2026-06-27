import * as vscode from "vscode";
import * as http from "http";

export class IllipChatPanel {
  static currentPanel: IllipChatPanel | undefined;
  private static _pendingMessage: string | undefined;

  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionUri: vscode.Uri;
  private _disposables: vscode.Disposable[] = [];

  static createOrShow(extensionUri: vscode.Uri) {
    if (IllipChatPanel.currentPanel) {
      IllipChatPanel.currentPanel._panel.reveal();
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "illipChat",
      "ILLIP AI",
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    );
    IllipChatPanel.currentPanel = new IllipChatPanel(panel, extensionUri);
  }

  static sendMessage(message: string) {
    if (IllipChatPanel.currentPanel) {
      IllipChatPanel.currentPanel._panel.webview.postMessage({ type: "prefill", message });
    } else {
      IllipChatPanel._pendingMessage = message;
    }
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._extensionUri = extensionUri;
    this._panel.webview.html = this._getHtml();

    this._panel.webview.onDidReceiveMessage(
      (msg) => {
        if (msg.type === "ready" && IllipChatPanel._pendingMessage) {
          this._panel.webview.postMessage({
            type: "prefill",
            message: IllipChatPanel._pendingMessage,
          });
          IllipChatPanel._pendingMessage = undefined;
        }
        if (msg.type === "send") {
          this._streamChat(msg.message);
        }
      },
      undefined,
      this._disposables
    );

    this._panel.onDidDispose(() => this._dispose(), null, this._disposables);
  }

  private _getServerUrl(): string {
    return (
      vscode.workspace.getConfiguration("illip").get<string>("serverUrl") ??
      "http://localhost:8000"
    );
  }

  private _streamChat(message: string) {
    const serverUrl = new URL(this._getServerUrl());
    const body = JSON.stringify({ message, include_memory: true });
    const options = {
      hostname: serverUrl.hostname,
      port: parseInt(serverUrl.port || "8000"),
      path: "/api/chat/stream",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
        Accept: "text/event-stream",
      },
    };

    const panel = this._panel;
    const req = http.request(options, (res) => {
      panel.webview.postMessage({ type: "start" });
      let buffer = "";
      res.on("data", (chunk: Buffer) => {
        buffer += chunk.toString("utf-8");
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const raw = line.slice(5).trim();
          if (raw === "[DONE]") {
            panel.webview.postMessage({ type: "done" });
            return;
          }
          try {
            const obj = JSON.parse(raw);
            if (obj.token) panel.webview.postMessage({ type: "token", token: obj.token });
            if (obj.tool_calls)
              panel.webview.postMessage({ type: "tool", names: obj.tool_calls });
            if (obj.routing)
              panel.webview.postMessage({ type: "routing", model: obj.routing.model });
          } catch {}
        }
      });
      res.on("end", () => panel.webview.postMessage({ type: "done" }));
    });

    req.on("error", (err) => {
      panel.webview.postMessage({
        type: "error",
        message: `Cannot connect to ILLIP at ${this._getServerUrl()}. Is it running?`,
      });
    });

    req.write(body);
    req.end();
  }

  private _getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ILLIP AI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size);
         background: var(--vscode-editor-background); color: var(--vscode-editor-foreground);
         display: flex; flex-direction: column; height: 100vh; }
  #messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
  .msg { padding: 8px 12px; border-radius: 6px; max-width: 90%; white-space: pre-wrap; line-height: 1.5; }
  .user { background: var(--vscode-button-background); color: var(--vscode-button-foreground);
          align-self: flex-end; }
  .assistant { background: var(--vscode-editorWidget-background);
               border: 1px solid var(--vscode-panel-border); align-self: flex-start; }
  .meta { font-size: 0.75em; opacity: 0.6; align-self: flex-start; }
  #input-area { display: flex; gap: 8px; padding: 10px; border-top: 1px solid var(--vscode-panel-border); }
  #input { flex: 1; background: var(--vscode-input-background); color: var(--vscode-input-foreground);
           border: 1px solid var(--vscode-input-border); border-radius: 4px;
           padding: 8px; resize: none; font-family: inherit; font-size: inherit; }
  #send { background: var(--vscode-button-background); color: var(--vscode-button-foreground);
          border: none; border-radius: 4px; padding: 8px 16px; cursor: pointer; }
  #send:hover { background: var(--vscode-button-hoverBackground); }
</style>
</head>
<body>
<div id="messages"></div>
<div id="input-area">
  <textarea id="input" rows="3" placeholder="Ask ILLIP AI anything... (Enter to send, Shift+Enter for newline)"></textarea>
  <button id="send">Send</button>
</div>
<script>
  const vscode = acquireVsCodeApi();
  const messages = document.getElementById('messages');
  const input = document.getElementById('input');
  let currentDiv = null;

  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addMeta(text) {
    const div = document.createElement('div');
    div.className = 'meta';
    div.textContent = text;
    messages.appendChild(div);
  }

  function send() {
    const msg = input.value.trim();
    if (!msg) return;
    addMsg('user', msg);
    input.value = '';
    vscode.postMessage({ type: 'send', message: msg });
  }

  document.getElementById('send').onclick = send;
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'start') {
      currentDiv = addMsg('assistant', '');
    } else if (msg.type === 'token' && currentDiv) {
      currentDiv.textContent += msg.token;
      messages.scrollTop = messages.scrollHeight;
    } else if (msg.type === 'done') {
      currentDiv = null;
    } else if (msg.type === 'tool') {
      addMeta('Using skills: ' + msg.names.join(', '));
    } else if (msg.type === 'routing') {
      addMeta('Model: ' + msg.model);
    } else if (msg.type === 'error') {
      addMsg('assistant', '[Error] ' + msg.message);
    } else if (msg.type === 'prefill') {
      input.value = msg.message;
      input.focus();
    }
  });

  vscode.postMessage({ type: 'ready' });
</script>
</body>
</html>`;
  }

  private _dispose() {
    IllipChatPanel.currentPanel = undefined;
    this._panel.dispose();
    this._disposables.forEach((d) => d.dispose());
  }
}
