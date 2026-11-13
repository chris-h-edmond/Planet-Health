import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AuthProvider } from "@/components/auth/auth-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Planet Health — AI-Powered Plant Monitoring",
    template: "%s · Planet Health",
  },
  description:
    "Planet Health uses computer vision to classify plant stress and estimate leaf count and plant age from a single photograph.",
  applicationName: "Planet Health",
  keywords: [
    "plant health",
    "computer vision",
    "greenhouse",
    "plant stress",
    "growth estimation",
    "agriculture",
  ],
  authors: [{ name: "Planet Health" }],
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/favicon.ico",
  },
  openGraph: {
    title: "Planet Health — AI-Powered Plant Monitoring",
    description:
      "Understand your plants through AI-powered vision. Stress classification and growth estimation from a single image.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F9F7" },
    { media: "(prefers-color-scheme: dark)", color: "#111714" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full`}
    >
      <head>
        {/* Applies the persisted theme before the first paint so that the
            page never flashes the wrong colour scheme. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full bg-background text-foreground antialiased">
        <ThemeProvider>
          <AuthProvider>
            {children}
            <Toaster />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
