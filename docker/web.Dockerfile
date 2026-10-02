FROM node:22-slim

# node_modules live in the bind-mounted web/ dir (git-ignored), installed via `make install`.
WORKDIR /work/web
EXPOSE 5174
CMD ["npm", "run", "dev"]
