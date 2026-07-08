import type { Metadata } from "next";
// Self-hosted variable fonts — bundled in node_modules, so the build never reaches a font CDN.
import "@fontsource-variable/fraunces/index.css";
import "@fontsource-variable/instrument-sans/index.css";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { ThemeProvider, themeNoFlashScript } from "@/components/ThemeProvider";
import { AcousticsProvider } from "@/lib/hooks/useAcoustics";
import { QueryProvider } from "@/components/QueryProvider";
import { ToastProvider } from "@/lib/hooks/useToast";
import { Dock } from "@/components/primitives/Dock";

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: { default: "Nova", template: "%s · Nova" },
  description:
    "Intelligence should feel like a relationship, not a tool. Nova remembers, notices, and continues — across years, not sessions.",
  applicationName: "Nova",
  openGraph: {
    title: "Nova",
    description: "Intelligence that remembers. A private study for thinking.",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F4F1EA" },
    { media: "(prefers-color-scheme: dark)", color: "#0B0B0D" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistMono.variable} h-full`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeNoFlashScript }} />
      </head>
      <body className="relative min-h-full">
        <ThemeProvider>
          <QueryProvider>
            <AcousticsProvider>
              <ToastProvider>
                {children}
                <Dock />
              </ToastProvider>
            </AcousticsProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
