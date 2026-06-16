"use client";

import { Accordion as Primitive } from "@base-ui/react/accordion";
import { ChevronRight } from "lucide-react";
import { type ComponentProps } from "react";

import { cn } from "../../lib/cn";

export function Accordion({ className, ...props }: ComponentProps<typeof Primitive.Root>) {
  return (
    <Primitive.Root
      className={(s) =>
        cn(
          "divide-fd-border bg-fd-card divide-y overflow-hidden rounded-lg border",
          typeof className === "function" ? className(s) : className,
        )
      }
      {...props}
    />
  );
}

export function AccordionItem({ children, ...props }: ComponentProps<typeof Primitive.Item>) {
  return <Primitive.Item {...props}>{children}</Primitive.Item>;
}

export function AccordionHeader({
  className,
  children,
  ...props
}: ComponentProps<typeof Primitive.Header>) {
  return (
    <Primitive.Header
      className={(s) =>
        cn(
          "not-prose text-fd-card-foreground has-focus-visible:bg-fd-accent flex scroll-m-24 flex-row items-center font-medium",
          typeof className === "function" ? className(s) : className,
        )
      }
      {...props}
    >
      {children}
    </Primitive.Header>
  );
}

export function AccordionTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof Primitive.Trigger>) {
  return (
    <Primitive.Trigger
      className={(s) =>
        cn(
          "group flex flex-1 items-center gap-2 px-3 py-2.5 text-start focus-visible:outline-none",
          typeof className === "function" ? className(s) : className,
        )
      }
      {...props}
    >
      <ChevronRight className="text-fd-muted-foreground size-4 shrink-0 transition-transform duration-200 group-data-[panel-open]:rotate-90" />
      {children}
    </Primitive.Trigger>
  );
}

export function AccordionContent({
  className,
  children,
  ...props
}: ComponentProps<typeof Primitive.Panel>) {
  return (
    <Primitive.Panel
      className={(s) =>
        cn(
          "h-(--accordion-panel-height) overflow-hidden transition-[height] ease-out data-[ending-style]:h-0 data-[starting-style]:h-0",
          typeof className === "function" ? className(s) : className,
        )
      }
      {...props}
    >
      {children}
    </Primitive.Panel>
  );
}
