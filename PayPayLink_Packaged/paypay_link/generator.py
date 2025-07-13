import random
import time
import asyncio

def rand_gen(n):
    STRING = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,0,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z".split(
        ",")
    return "".join(random.choice(STRING) for i in range(n))

def generate_links(count, delay, output, logger=print, cancel_event: asyncio.Event | None = None, queue: asyncio.Queue | None = None):
    """Generates links and saves them to a file or a queue."""
    links = []
    logger(f"Generating {count} links...")
    for i in range(count):
        if cancel_event and cancel_event.is_set():
            logger("Generation cancelled by user.")
            break
        link_i = rand_gen(16)
        link = "https://pay.paypay.ne.jp/" + link_i
        if queue:
            queue.put_nowait(link)
        else:
            links.append(link)
        logger(f"Generated link: {link}")
        if delay > 0:
            time.sleep(delay)

    if not queue:
        try:
            with open(output, "w", encoding="utf-8") as f:
                for link in links:
                    f.write(f"{link}\n")
            logger(f"\nSuccessfully generated {len(links)} links and saved to {output}")
        except IOError as e:
            logger(f"\n[ERROR] Could not write to file {output}: {e}")

def generate_single_link(delay, logger=print):
    """Generates a single link."""
    link_i = rand_gen(16)
    link = "https://pay.paypay.ne.jp/" + link_i
    logger(f"Generated link: {link}")
    if delay > 0:
        time.sleep(delay)
    return link