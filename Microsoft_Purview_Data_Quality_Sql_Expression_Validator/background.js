/**
 * Strip the `Origin` header from requests to login.microsoftonline.com so that
 * Azure AD does not trigger AADSTS9002326 ("Cross-origin token redemption is
 * permitted only for the Single-Page Application client-type").
 *
 * client_credentials flows work fine server-side; the browser simply adds an
 * Origin header that AAD rejects. Removing it here makes the request
 * indistinguishable from a server-side call.
 */
browser.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const headers = (details.requestHeaders || []).filter(
      (h) => h.name.toLowerCase() !== 'origin'
    );
    return { requestHeaders: headers };
  },
  {
    urls: [
      'https://login.microsoftonline.com/*',
    ],
  },
  ['blocking', 'requestHeaders']
);
