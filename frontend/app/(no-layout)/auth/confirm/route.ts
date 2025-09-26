import type { EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { createClient } from "@/utils/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/";

  const code = searchParams.get("code");
  
  const supabase = await createClient();

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      console.error("OAuth session exchange error:", error.message);
      redirect(`/login?error=${encodeURIComponent("Authentication failed. Please try again.")}`);
    }
    redirect(next);
  }

  if (token_hash && type) {
    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash,
    });
    if (error) {
      console.error("OTP verification error:", error.message);
      redirect(`/login?error=${encodeURIComponent("Invalid or expired link. Please try again.")}`);
    }
    redirect(next);
  }

  console.error("Auth confirm called without valid parameters");
  redirect(`/login?error=${encodeURIComponent("Invalid authentication request.")}`);
}
