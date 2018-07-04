package main

// DISCONTINUED
// mount already has setuid activated. It checks the real UID
// so this is not a viable solution for mounting volumes as root

import (
    "os"
    "fmt"
    "os/exec"
    "syscall"
)

func umountVolume(mountPoint string) {
    _, err := exec.Command("umount", mountPoint).Output()
    if err != nil {
        exitError("The volume could not be unmounted.")
    }
}

func mountVolume(imgFile string, mountPoint string) {
    _, err := exec.Command("mount", imgFile, mountPoint).Output()
    if err != nil {
        exitError("The volume could not be mounted.")
    }
}

func exitError(err string) {
    fmt.Fprintf(os.Stderr, err + "\n")
    os.Exit(1)
}

func main() {

    fmt.Printf("Effective UID: %d\n", syscall.Geteuid())
    fmt.Printf("Real UID: %d\n", syscall.Getuid())

    if len(os.Args) != 4 {
        exitError("Usage: volm <source_device> <mount_point>")
    }

    imgFile := os.Args[2]

    // Check if the img file exists
    if _, err := os.Stat(imgFile); err == nil {
        mountPoint := os.Args[3]

        // Check if the mount point exists
        if _, err := os.Stat(mountPoint); err == nil {
            switch op := os.Args[1]; op {
                case "mount":
                    mountVolume(imgFile, mountPoint)
                case "umount":
                    umountVolume(mountPoint)
            }
            return
        }
        exitError("Cannot access the mount point.")
    }
    exitError("Cannot access the source device.")
}
