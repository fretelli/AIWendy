import { redirect } from "next/navigation";

export default function Page() { redirect("/agent/market?tab=macro&view=rates&period=1Y"); }
