-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

-- quit
vim.keymap.set({ "n", "v" }, "<C-q>", "<Cmd>confirm q<CR>", { desc = "Quit" })
vim.keymap.set("i", "<C-q>", "<Esc><Cmd>confirm q<CR>a", { desc = "Quit" })

-- save
vim.keymap.set({ "n", "v" }, "<C-s>", "<Cmd>w<CR>", { desc = "Save" })
vim.keymap.set("i", "<C-s>", "<Esc><Cmd>w<CR>a", { desc = "Save" })
