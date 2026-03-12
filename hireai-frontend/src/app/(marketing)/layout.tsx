import { Navbar } from "@/components/marketing/navbar";
import { Chatbot } from "@/components/shared/chatbot";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      <main className="pt-16">{children}</main>
      <Chatbot />
    </>
  );
}
