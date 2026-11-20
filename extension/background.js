importScripts("data.js");

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "lookup") {
    lookup(message.store, message.code).then(
      (result) => sendResponse({ result }),
      (error) => sendResponse({ error: String(error) }),
    );

    // the answer is sent asynchronously
    return true;
  }
});
