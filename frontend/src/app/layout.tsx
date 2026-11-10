import type { Metadata } from "next";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/literata";
import "./globals.css";

export const metadata: Metadata = {
  title: "Viva: interviews written from the textbook",
  description: "A role-based screening interview whose questions are generated from your resume and a role-specific knowledge base.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-[1240px] px-3 py-4 sm:px-6 sm:py-8">{children}</div>
      </body>
    </html>
  );
}
