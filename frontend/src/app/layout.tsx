import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { ProjectProvider } from "@/hooks/useProjectContext";
import { CommandBar } from "@/components/CommandBar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AquaBrain - MEP Intelligence",
  description: "AI-powered MEP Clash Detection and Engineering Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="he" dir="rtl">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <LanguageProvider defaultLang="he">
          <ProjectProvider>
            {/* Main content with bottom padding for CommandBar */}
            <div className="pb-16">
              {children}
            </div>
            {/* Global Command Bar - appears on every page */}
            <CommandBar />
          </ProjectProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
