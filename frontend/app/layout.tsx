import type { Metadata } from "next";

import { SiteFooter, SiteHeader } from "@/components/nav";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "VisaGuard — check your visa documents before you submit",
  description:
    "Upload your visa document set and get a rejection-risk report before you submit. Missing documents, name mismatches, funds and photo compliance, checked against a versioned per-corridor checklist.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <AuthProvider>
          <SiteHeader />
          <main className="flex-1">{children}</main>
          <SiteFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
