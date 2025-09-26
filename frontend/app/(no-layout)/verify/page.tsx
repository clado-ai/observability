import { logout } from "@/logic/auth";

export default async function VerifyPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-sm mx-auto">
      <div className="flex flex-col items-center justify-center">
        <div className="flex flex-row items-center justify-center mb-8 gap-2">
          <i className="bx bx-check bg-green-50 text-green-500 rounded-full p-2"></i>
        </div>
        <p className="text-xl">Follow the link in your email to get started!</p>
      </div>
      <br />
      <div className="flex flex-row items-center justify-center w-full">
        <div className="w-full h-[1px] bg-muted" />
        <p className="text-muted-foreground text-xs mx-4 whitespace-nowrap">
          or{" "}
          <button
            className="text-black hover:italic"
            type="button"
            onClick={logout}
          >
            sign out
          </button>{" "}
          and try again?
        </p>
        <div className="w-full h-[1px] bg-muted" />
      </div>
    </div>
  );
}
