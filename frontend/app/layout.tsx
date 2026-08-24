import type { Metadata, Viewport } from "next";

import { SiteFooter, SiteHeader } from "@/components/nav";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const SITE_NAME = "VisaGuard";
const TAGLINE = "Check your visa file before the consulate does";
const DESCRIPTION =
  "Upload your visa application bundle and get a rejection-risk report before you submit. Missing documents, name mismatches, funds, dates and photo compliance, checked against a versioned per-corridor checklist.";

// Absolute URLs in Open Graph tags need an origin. Falls back to a relative
// base in local development rather than baking a placeholder domain into tags.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL;

export const metadata: Metadata = {
  ...(siteUrl ? { metadataBase: new URL(siteUrl) } : {}),
  title: {
    default: `${SITE_NAME} — ${TAGLINE}`,
    template: `%s · ${SITE_NAME}`,
  },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: [
    "visa checklist",
    "visa document check",
    "Schengen visa refusal",
    "visa rejection risk",
    "visa application review",
    "immigration paperwork",
  ],
  authors: [{ name: SITE_NAME }],
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME} — ${TAGLINE}`,
    description: DESCRIPTION,
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — ${TAGLINE}`,
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  formatDetection: { telephone: false, address: false },
};

export const viewport: Viewport = {
  themeColor: "#080D18",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Inter for UI, Sora for headings, JetBrains Mono for versions and IDs. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        {/* The hero footage and its poster live on these two hosts. */}
        <link rel="preconnect" href="https://images.pexels.com" />
        <link rel="preconnect" href="https://videos.pexels.com" />
      </head>
      <body className="flex min-h-screen flex-col bg-surface text-ink antialiased">
        {/* Keyboard users should not have to tab past the whole nav on every page. */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-neon-600 focus:px-4 focus:py-2.5 focus:text-sm focus:font-semibold focus:text-white"
        >
          Skip to content
        </a>

        <AuthProvider>
          <SiteHeader />
          <main id="main" className="flex-1">
            {children}
          </main>
          <SiteFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
