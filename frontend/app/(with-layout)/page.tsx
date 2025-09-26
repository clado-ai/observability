import Explore from "@/components/explore";
import { listServers } from "@/logic/servers";
export default async function Page() {
  const result = await listServers();

  console.log(result);

  return (
    <div className="p-8 px-4 w-full flex flex-col items-center justify-start pt-12 flex-1">
      <Explore servers={result.servers} />
    </div>
  );
}
