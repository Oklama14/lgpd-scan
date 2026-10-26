import * as CookieConsent from 'vanilla-cookieconsent';

export function iniciarConsentimento() {
  window.gtag('consent', 'default', { analytics_storage: 'denied', ad_storage: 'denied' });
  CookieConsent.run({
    categories: { necessary: { readOnly: true }, analytics: {} },
    onConsent: () => window.gtag('consent', 'update', { analytics_storage: 'granted' }),
  });
}
