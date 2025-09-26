import type { Metadata } from "next";
import "@/app/globals.css";
import type { User } from "@supabase/supabase-js";
import Image from "next/image";
import logo from "@/app/assets/logo.svg";
import BillingCard from "@/components/billing/billing-card";
import NavButton from "@/components/ui/nav-button";
import Subtitle from "@/components/ui/subtitle";
import UserComponent from "@/components/user";
import { createClient } from "@/utils/supabase/server";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import None from "@/components/none";

export const metadata: Metadata = {
  title: "Clado",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="w-full h-full bg-muted p-4 flex flex-row items-center justify-center gap-4">
      <div className="flex flex-col items-start justify-start p-4 px-0 w-full max-w-64 h-full">
        <div className="flex flex-row items-center justify-between w-full px-4">
          <div className="flex flex-row items-center justify-start">
            <Image src={logo} alt="Logo" className="w-5 h-5 mr-2" />
            <p className="text-xl">Clado</p>
          </div>
          {
            user && (
              <UserComponent user={user} />
            )
          }
        </div>
        {
          !user && (
            <>
            <div className="flex-1"></div>
            <div className="flex flex-col items-center justify-center w-full gap-4">
              <None>You are not signed in.</None>
              <Link href="/login">
                <Button>Login</Button>
              </Link>
            </div>
            <div className="flex-1"></div>
            </>
          )
        }
        {
          user && (
            <>
         <br />
        <NavButton href="/onboard" props={{ variant: "outline" }}>
          <i className="bx bx-rocket"></i>Add to your Agent{" "}
          <div className="flex-1"></div>
          <i className="bx bx-right-arrow-alt"></i>
        </NavButton>
        <NavButton href="/playground">
          <i className="bx bx-test-tube"></i>Playground
        </NavButton>
        <br />
        <Subtitle className="px-4 mb-2" text="Integrate" />
        <NavButton href="/">
          <i className="bx bx-compass"></i>Browse Servers
        </NavButton>
        <NavButton href="/keys">
          <i className="bx bx-key"></i>API Keys
        </NavButton>
        <NavButton href="/usage">
          <i className="bx bx-list-ul"></i>Usage & Analytics
        </NavButton>
        {/* <NavButton href="/docs">
          <i className="bx bx-book"></i>Documentation
        </NavButton> */}
        {/* <NavButton href="/billing">
          <i className="bx bx-credit-card"></i>Billing
        </NavButton> */}
        <br />
        <Subtitle className="px-4 mb-2" text="Add your tools to clado" />
        <NavButton href="/servers/new">
          <i className="bx bx-plus"></i>Add Server
        </NavButton>
        <NavButton href="/servers">
          <i className="bx bx-briefcase"></i>My Servers
        </NavButton>
        {/* <NavButton href="/wallet">
          <i className="bx bx-wallet"></i>Wallet
        </NavButton> */}
        <div className="flex-1"></div>
        <BillingCard />
        <Subtitle className="px-4 mb-2" text="More" />
        <NavButton href="https://cal.com/clado/chat?duration=15">
          <i className="bx bx-video"></i>Book a Meeting
        </NavButton>
        <NavButton href="tel:+16476151655">
          <i className="bx bx-phone"></i>Call an Engineer
        </NavButton>
        <NavButton href="mailto:founders@clado.ai">
          <i className="bx bx-envelope"></i>Email Us
        </NavButton>   
            </>
          )
        }        <svg className="h-0 w-0">
          <defs>
            <clipPath id="SquircleClip-2" clipPathUnits="objectBoundingBox">
              <path
                d="M 0,0.5
                C 0,0.0575  0.0575,0  0.5,0
                  0.9425,0  1,0.0575  1,0.5
                  1,0.9425  0.9425,1  0.5,1
                  0.0575,1  0,0.9425  0,0.5"
              ></path>
            </clipPath>
          </defs>
        </svg>
      </div>
      <div className="flex-1 flex flex-col h-full overflow-auto bg-white rounded-md">
        <div className="flex flex-col items-center justify-start max-w-5xl mx-auto w-full flex-1">
          {children}
        </div>
      </div>
    </div>
  );
}
