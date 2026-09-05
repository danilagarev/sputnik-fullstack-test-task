import type { Metadata } from "next";
import "bootstrap/dist/css/bootstrap.min.css";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Файлообменник",
  description: "Загрузка файлов, проверка на угрозы и лента алертов",
};

// The icon is served through the app/favicon.ico file convention, which is the
// only form that survives basePath: a hand-written <link href="/favicon.ico">
// misses the "/test" prefix, and "/public/..." was never a valid URL at all.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
