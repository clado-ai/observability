"use client";

import type { User } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/utils/supabase/client";

export default function UserComponent({ user }: { user: User }) {
  const supabase = createClient();
  const router = useRouter();

  return (
    <div className="flex flex-row items-center justify-center">
      <DropdownMenu>
        <DropdownMenuTrigger>
          <Avatar className="cursor-pointer">
            <AvatarImage src={user.user_metadata.avatar_url} />
            <AvatarFallback className="bg-white">
              {user.email?.charAt(0)}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>{user.email}</DropdownMenuLabel>
          <DropdownMenuItem
            onClick={() =>
              supabase.auth.signOut().then(() => {
                router.push("/login");
              })
            }
          >
            <i className="bx bx-log-out"></i> Logout
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
