import type { Metadata } from "next";
import "@/app/globals.css";
import QueryWrap from "@/components/root/query-wrap";

export const metadata: Metadata = {
  title: "Clado",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased p-0 m-0 w-full h-screen overflow-x-hidden">
        <QueryWrap>{children}</QueryWrap>
      </body>
    </html>
  );
}
