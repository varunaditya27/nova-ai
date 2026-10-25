import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./pointer.css";
import "./scrollbar.css";
import { ThemeProvider, lightNoFlashScript } from "@/components/ThemeProvider";
import { AcousticsProvider } from "@/lib/hooks/useAcoustics";
import { QueryProvider } from "@/components/QueryProvider";
import { ToastProvider } from "@/lib/hooks/useToast";
import { AppShell } from "@/components/shell/AppShell";

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: { default: "Nova", template: "%s · Nova" },
  description:
    "A companion that remembers you, notices how you’re doing, and keeps going — across years, not sessions. Private, and yours.",
  applicationName: "Nova",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf7f5" },
    { media: "(prefers-color-scheme: dark)", color: "#1c1917" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning data-light="day">
      <head>
        <script dangerouslySetInnerHTML={{ __html: lightNoFlashScript }} />
      </head>
      <body>
        <ThemeProvider>
          <QueryProvider>
            <AcousticsProvider>
              <ToastProvider>
                <AppShell>{children}</AppShell>
              </ToastProvider>
            </AcousticsProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
