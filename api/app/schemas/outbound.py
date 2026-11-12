from pydantic import BaseModel


class AllowedHosts(BaseModel):
    # Hosts an admin allowed (exact names or *.domain, runtime setting
    # <kind>.source_hosts). Empty: any host, but never a loopback,
    # link-local, multicast or reserved address.
    hosts: list[str] = []
