import Image from "next/image";
import Link from "next/link";
import logo from "@/app/assets/logo.svg";
import SubmitButton from "@/components/submit";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login, signInWithGoogle } from "@/logic/auth";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const error = (await searchParams).error;
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-sm mx-auto">
      <div className="flex flex-row items-center justify-center">
        <Image src={logo} alt="Logo" className="w-5 h-5 mr-2" />
        <p className="text-xl">Sign into Clado</p>
      </div>
      <br />
      <form className="w-full">
        <Button
          variant="outline"
          className="w-full"
          type="submit"
          formAction={signInWithGoogle}
        >
          <i className="bx bxl-google"></i>
          Continue with Google
        </Button>
      </form>
      <br />
      <div className="flex flex-row items-center justify-center w-full">
        <div className="w-full h-[1px] bg-muted" />
        <p className="text-muted-foreground text-xs mx-4">or</p>
        <div className="w-full h-[1px] bg-muted" />
      </div>
      <br />

      <form className="flex flex-col gap-2 w-full" action={login}>
        <Label htmlFor="email" className="text-muted-foreground">
          Email address
        </Label>
        <Input
          className="mb-3"
          placeholder="rohin@clado.ai"
          id="email"
          name="email"
          type="email"
          required
        />
        <Label htmlFor="password" className="text-muted-foreground">
          Password
        </Label>
        <Input
          placeholder="********"
          id="password"
          name="password"
          type="password"
          required
        />
        <br />
        {error && (
          <Alert variant="destructive" className="mb-2">
            <i className="bx bx-alert"></i>
            <AlertTitle>{error}</AlertTitle>
          </Alert>
        )}
        <SubmitButton>
          Continue
          <i className="bx bx-right-arrow-alt"></i>
        </SubmitButton>
        <p className="text-muted-foreground text-xs mt-2">
          Don't have an account?{" "}
          <Link className="hover:italic text-primary" href="/register">
            Sign up <i className="bx bx-right-arrow-alt"></i>
          </Link>
        </p>
      </form>
    </div>
  );
}
