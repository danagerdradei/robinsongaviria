# Usa la imagen base de Nginx
FROM nginx:alpine

# Copiar el archivo de configuración personalizado de Nginx
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Copiar los archivos del sitio a la carpeta predeterminada de Nginx
COPY . /usr/share/nginx/html

# Exponer el puerto 8000
EXPOSE 80

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]