import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://mydatatalk.ai"),
  title: "MyDataTalk — Ask your data anything",
  description:
    "Connect any database, pick any AWS Bedrock model, and query in plain English. Get SQL, charts, and answers — no SQL required.",
  openGraph: {
    title: "MyDataTalk",
    description: "Plain English → SQL → Results. Any Bedrock model. Multiple databases.",
    url: "https://mydatatalk.ai",
    siteName: "MyDataTalk",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "MyDataTalk",
    description: "Plain English → SQL → Results. Any Bedrock model. Multiple databases.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
