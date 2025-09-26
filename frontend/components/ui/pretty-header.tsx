export default function PrettyHeader({ title }: { title: string }) {
  return (
    <div className="border-b 2xl:border-b-0 w-full px-4 pb-2 mb-4 2xl:mb-0 2xl:pb-0 relative ">
      <p className="absolute float-left right-full w-24 mr-4 text-muted-foreground hidden 2xl:block">
        {title}
      </p>
      <p className="block 2xl:hidden underline underline-offset-14">{title}</p>
    </div>
  );
}
