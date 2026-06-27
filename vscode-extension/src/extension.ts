import * as vscode from "vscode";
import { IllipChatPanel } from "./chatPanel";

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand("illip.openChat", () => {
      IllipChatPanel.createOrShow(context.extensionUri);
    }),

    vscode.commands.registerCommand("illip.explainSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const code = editor.document.getText(selection);
      if (!code.trim()) {
        vscode.window.showWarningMessage("Select some code first.");
        return;
      }
      const lang = editor.document.languageId;
      IllipChatPanel.createOrShow(context.extensionUri);
      IllipChatPanel.sendMessage(`Explain this ${lang} code:\n\`\`\`${lang}\n${code}\n\`\`\``);
    }),

    vscode.commands.registerCommand("illip.askAboutFile", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const filename = editor.document.fileName.split(/[\\/]/).pop() ?? "file";
      const content = editor.document.getText().slice(0, 3000);
      const lang = editor.document.languageId;
      const question = await vscode.window.showInputBox({
        prompt: `Ask ILLIP AI about ${filename}`,
        placeHolder: "What does this file do?",
      });
      if (!question) return;
      IllipChatPanel.createOrShow(context.extensionUri);
      IllipChatPanel.sendMessage(
        `File: ${filename}\n\`\`\`${lang}\n${content}\n\`\`\`\n\nQuestion: ${question}`
      );
    })
  );
}

export function deactivate() {}
