import Link from "next/link";
import OnClick from "@/components/onclick";
import CopyButton from "@/components/ui/copy-button";
import PrettyHeader from "@/components/ui/pretty-header";
import { createKey, readKey } from "@/logic/keys";

export default async function Page() {
  const key = await readKey();

  return (
    <div className="p-8 px-4 w-full flex flex-col items-start justify-start flex-1">
      <p className="text-3xl font-medium px-4">Adding Clado to your Agent</p>

      <br />
      <br />

      <PrettyHeader title="Authentication" />
      <div className="px-4 mb-2">
        {key ? (
          <>
            <p className="mb-2">Your API key is: {key}.</p>{" "}
            <CopyButton full={true} text={key} />
          </>
        ) : (
          <>
            <p className="mb-2">No key has been generated.</p>
            <OnClick
              props={{
                type: "button",
              }}
              onClick={createKey}
            >
              Generate key?
            </OnClick>
          </>
        )}
      </div>

      <br />
      <br />
      <PrettyHeader title="Browser Use" />
      <p className="px-4 mb-2">Use this snippet:</p>
      <div className="2xl:pl-4">
        <div className="p-4 bg-muted rounded-md flex flex-row items-center justify-start gap-4 font-mono text-sm">
          <i className="bx bx-code"></i>
          Code
          <div className="flex-1"></div>
          {/* <CopyButton text={ENV_STUFF} /> */}
        </div>
      </div>

      <br />
      <br />
      <PrettyHeader title="Need Help?" />
      <div className="px-4">
        <p className="mb-2">
          Setup an{" "}
          <Link
            className="underline hover:italic"
            target="_blank"
            href="https://cal.com/clado/chat?duration=15"
          >
            onboarding call
          </Link>{" "}
          with us for any questions!
        </p>
      </div>
    </div>
  );
}
