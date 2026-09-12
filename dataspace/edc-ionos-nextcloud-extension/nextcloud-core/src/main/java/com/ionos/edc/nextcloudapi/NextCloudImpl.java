package com.ionos.edc.nextcloudapi;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import okhttp3.*;
import org.eclipse.edc.spi.EdcException;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import java.io.InputStream;

public class NextCloudImpl implements NextCloudApi {
    private OkHttpClient client = new OkHttpClient();
    private String basicUrl = "";
    private String username = "";
    private String password = "";

    public NextCloudImpl(String basicUrl, String username, String password) {
        this.basicUrl = basicUrl;
        this.username = username;
        this.password = password;
    }

    @Override
    public void nextCloudApi(String url, String username, String password) {
        this.basicUrl = url;
        this.username = username;
        this.password = password;
    }

    @Override
    public String generateUrlDownload(String filePath, String fileName) {
        String urlPart = "/ocs/v2.php/apps/dav/api/v1/direct?fileId=";
        String fileId = retrieveId(filePath, fileName);
        String url = basicUrl + urlPart + fileId;

        Request request = new Request.Builder()
                .url(url)
                .addHeader("OCS-APIRequest", "true")
                .addHeader("Authorization", Credentials.basic(username, password))
                .post(RequestBody.create(null, new byte[0]))
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new EdcException("Unexpected code " + response);
            }

            String xmlResponse = response.body().string();
            Document document = Jsoup.parse(xmlResponse);
            String OC_URL = "url";

            return document.select(OC_URL).text();

        } catch (Exception e) {
            throw new EdcException("Error generation URL" + e);
        }

    }

    @Override
    public byte[] downloadFile( String url) {

        Request request = new Request.Builder()
                .url(url)
                .build();
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }

            InputStream in = response.body().byteStream();

            return in.readAllBytes();
        } catch (IOException e) {
            throw new EdcException("Error when downloading the file: " + e);
        }
    }

    @Override
    public void uploadFile(String filePath, String fileName, ByteArrayInputStream part) {
        String urlPart = "/remote.php/dav/files/" + username + "/";
        String url = basicUrl + urlPart +filePath+ "/" +fileName;

        MediaType mediaType = MediaType.parse("application/octet-stream");

        RequestBody body = RequestBody.Companion.create(part.readAllBytes(), mediaType);

        Request request = new Request.Builder()
                .url(url)
                .addHeader("OCS-APIRequest", "true")
                .addHeader("Authorization", Credentials.basic(username, password))
                .put(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
        } catch (Exception e) {
            throw new EdcException("Error uploading file: "+ e);
        }
    } 

   /*@Override
    public void uploadFile(String filePath, String fileName, InputStream part) { 
        String urlPart = "/remote.php/dav/files/" + username + "/";
        String url = basicUrl + urlPart + filePath + "/" + fileName;

        
        RequestBody body = new RequestBody() {
            @Override
            public MediaType contentType() {
                return MediaType.parse("application/octet-stream");
            }

            @Override
            public long contentLength() {
                return -1;
            }

            @Override
            public void writeTo(okio.BufferedSink sink) throws IOException {
                try (okio.Source source = okio.Okio.source(part)) {
                    sink.writeAll(source); // Stream the data directly to the sink
                }
            }
        };

        Request request = new Request.Builder()
                .url(url)
                .addHeader("OCS-APIRequest", "true")
                .addHeader("Authorization", Credentials.basic(username, password))
                .put(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
        } catch (Exception e) {
            throw new org.eclipse.edc.spi.EdcException("Error uploading file: " + e.getMessage(), e);
        }
    } */

    @Override
    public void fileShare(String filePath, String fileName, String shareWith, String shareType, String permissionType, String expireDate) {
        String FILESHARE_ADDRESS = "/ocs/v2.php/apps/files_sharing/api/v1/shares?";
        String url = basicUrl + FILESHARE_ADDRESS +
                "path=" +filePath +"/"+ fileName + "&shareType="+shareType+"&shareWith=" + shareWith  +"&publicUpload=false&permissions=" + permissionType + "&expireDate=" + expireDate;

        HttpUrl urlHttp = HttpUrl.parse(url);
        Request request = new Request.Builder()
                .url(urlHttp)
                .addHeader("OCS-APIRequest", "true")
                .addHeader("Authorization", Credentials.basic(username, password))
                .post(RequestBody.create(null, ""))
                .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new EdcException("Unexpected code " + response);
            }
        } catch (IOException e) {
            throw new EdcException("Error when granting sharing permissions: "+ e);
        }
    }

    private String retrieveId(String path, String fileName) {
        String urlPart = "/remote.php/dav/files/" + username ;
        String url = basicUrl + urlPart+"/" + path+"/"+fileName;
        String body = "<?xml version=\"1.0\"?>\n" +
                "<d:propfind  xmlns:d=\"DAV:\" xmlns:oc=\"http://owncloud.org/ns\" xmlns:nc=\"http://nextcloud.org/ns\">\n" +
                "  <d:prop>\n" +
                "  <oc:fileid />\n" +
                "  </d:prop>\n" +
                "</d:propfind>";

        Request request = new Request.Builder()
                .url(url)
                .addHeader("OCS-APIRequest", "true")
                .addHeader("Authorization", Credentials.basic(username, password))
                .method("PROPFIND", RequestBody.create(null, body))
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new EdcException("Unexpected code " + response);
            }

            String xmlResponse = response.body().string();
            Document document = Jsoup.parse(xmlResponse);
            String OC_FILEID = "oc|fileid";
            String fileId = document.select(OC_FILEID).text();

            return fileId;
        } catch (IOException e) {
            throw new EdcException("Error fetching id from file: "+e);
        }
    }
}