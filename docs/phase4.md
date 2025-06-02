# Tinker - Phase 4

In Phase 3, we added a feature for Tinker to interface with shell (with approval prompt). I'm not comfortable with running anything like this. Too scary. It could do `rm -rf` on things I don't want deleted.

In Phase 4, let's find a way to do this little more safely. When the process runs, could you run docker?

I want to do something like this.

- When tinker starts, it will start a docker container. 
- It is persistent one. So if you turn it off, it can still be brought back up next time tinker runs.
- docker instance can live within .tinker folder.