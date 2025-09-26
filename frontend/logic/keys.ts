"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/utils/supabase/server";
import { getAPIKey } from "@/utils/utils";

export const readKey = async () => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { data } = await supabase
    .from("keys")
    .select("*")
    .eq("user_id", user?.id ?? "")
    .single();

  return data?.key;
};

export const createKey = async () => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const key = await getAPIKey(user?.id ?? "");
  const { error } = await supabase
    .from("keys")
    .insert({ key, user_id: user?.id ?? "" });
  if (error) {
    console.error("Error creating key:", error.message);
    throw new Error("Error creating key");
  }

  revalidatePath("/onboard");
};
