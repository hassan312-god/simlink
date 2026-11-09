import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Simlink — Vos simulations, augmentées par l’IA",
  description: "Explorez des concepts de connecteurs MCP et de skills pour relier vos jeux de simulation à Claude, Gemini et GPT.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
