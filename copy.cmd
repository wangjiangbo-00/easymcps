robocopy ./dist/easy_mcps/_internal/config ./dist/easy_mcps/config /E
robocopy ./dist/easy_mcps/_internal/templates ./dist/easy_mcps/templates /E
robocopy ./dist/easy_mcps/_internal/servers ./dist/easy_mcps/servers /E
robocopy ./dist/easy_mcps/_internal/static ./dist/easy_mcps/static /E

rmdir /s /q “./dist/easy_mcps/_internal/config”
rmdir /s /q ./dist/easy_mcps/_internal/templetes
rmdir /s /q ./dist/easy_mcps/_internal/servers
rmdir /s /q ./dist/easy_mcps/_internal/static
