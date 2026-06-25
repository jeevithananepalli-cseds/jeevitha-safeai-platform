import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafeAI — Women's Safety & Emergency Response",
  description:
    "AI-powered safety platform: SOS activation, emergency contacts, location sharing, and intelligent risk assessment.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
