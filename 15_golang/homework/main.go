package main

import (
	"bufio"
	"compress/gzip"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"github.com/spf13/viper"
	"log"
	"os"
	"otus"
	"path"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
)

var pattern = flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "Glob pattern to search files")
var configPath = flag.String("config", "", "Path to the config file")

type config struct {
	MemcConns map[string]string
	Memc      struct {
		RetryTimeout           time.Duration
		ConnTimeout            time.Duration
		RetryCount             int
		MaxConnectionPerServer int
	}
	MaxOpenFiles       int
	MaxLineAnalyzerMul int
}

type filePaths struct {
	filePath    string
	newFilePath string
}

func readFile(fileNamesCh chan filePaths, lineCh chan string, wg *sync.WaitGroup) {
	defer wg.Done()
	for p := range fileNamesCh {
		log.Println(p.filePath)
		file, err := os.Open(p.filePath)
		if err != nil {
			log.Fatal(err)
		}
		gz, err := gzip.NewReader(file)
		scanner := bufio.NewScanner(gz)
		for scanner.Scan() {
			lineCh <- scanner.Text()
		}

		if err := scanner.Err(); err != nil {
			log.Fatal(err)
		}
		log.Printf("Close file:\n%v", p.filePath)
		file.Close()
		// Add . prefix to the file name if all ok
		os.Rename(p.filePath, p.newFilePath)
		log.Printf("File renamed to:\n%v", p.newFilePath)
	}
}
func analyzeLine(lineCh chan string, chMap map[string]chan memcache.Item, wg *sync.WaitGroup) {
	defer wg.Done()
OUTER:
	for line := range lineCh {
		lineParts := strings.Split(line, "\t")
		if len(lineParts) != 5 {
			log.Printf("Can't split line:\n%s", line)
			continue
		}

		devType, devId := lineParts[0], lineParts[1]
		if devType == "" || devId == "" {
			log.Println("Empty devType or devId")
			continue
		}

		lat, err := strconv.ParseFloat(lineParts[2], 64)
		if err != nil {
			log.Fatalf("Can't convert %s to float64", lineParts[2])
			continue
		}
		lon, err := strconv.ParseFloat(lineParts[3], 64)
		if err != nil {
			log.Fatalf("Can't convert %s to float64", lineParts[2])
			continue
		}
		var rawApps []uint32
		for _, v := range strings.Split(lineParts[4], ",") {
			v64, err := strconv.ParseUint(v, 10, 32)
			if err != nil {
				log.Fatalf("Can't convert %s to uint64", v)
				continue OUTER

			}
			v32 := uint32(v64)
			rawApps = append(rawApps, v32)
		}

		appInstalled := otus.UserApps{
			Lat:  proto.Float64(lat),
			Lon:  proto.Float64(lon),
			Apps: rawApps,
		}
		data, err := proto.Marshal(&appInstalled)
		if err != nil {
			log.Fatal("marshaling error: ", err)
		}
		key := fmt.Sprintf("%v:%v", devType, devId)
		ch := chMap[devType]
		msg := memcache.Item{
			Key:   key,
			Value: data,
		}
		ch <- msg
	}
}

func sendMemc(ch chan memcache.Item, connString string, group *sync.WaitGroup, c config) {
	conn := memcache.New(connString)
	conn.Timeout = time.Second * c.Memc.ConnTimeout
	for item := range ch {
		// Realisation of reconnect count
		for i := 0; i < c.Memc.RetryCount; i++ {
			err := conn.Set(&item)
			if err != nil {
				log.Panicf("Can't set value. Something wrong:\n", err)
				time.Sleep(time.Second * c.Memc.RetryTimeout)
			}
		}
	}
	log.Printf("Sending done for %v", connString)
	group.Done()
}

func main() {
	flag.Parse()
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(*configPath)
	err := viper.ReadInConfig()
	if err != nil {
		panic(fmt.Errorf("Error config file: %s \n", err))
	}

	var configLocal config
	err2 := viper.Unmarshal(&configLocal)
	if err2 != nil {
		log.Fatalf("unable to decode into struct, %v", err)
	}

	filePathList, err := filepath.Glob(*pattern)
	if err != nil {
		log.Fatalf("unable to decode into struct, %v", err)
	}
	if filePathList == nil {
		log.Println("No files found, exit.")
		return
	}

	var wgConnMemc sync.WaitGroup
	memcChannelsMap := make(map[string]chan memcache.Item)
	for key, connString := range configLocal.MemcConns {
		ch := make(chan memcache.Item)
		memcChannelsMap[key] = ch
		for i := 0; i < configLocal.Memc.MaxConnectionPerServer; i++ {
			wgConnMemc.Add(1)
			go sendMemc(ch, connString, &wgConnMemc, configLocal)
		}
	}

	var wgAnalyzeLine sync.WaitGroup
	analyzeLineCh := make(chan string)

	for i := 0; i < runtime.NumCPU()*configLocal.MaxLineAnalyzerMul; i++ {
		wgAnalyzeLine.Add(1)
		go analyzeLine(analyzeLineCh, memcChannelsMap, &wgAnalyzeLine)
	}

	var wgReadFiles sync.WaitGroup
	fileNamesCh := make(chan filePaths)

	for i := 0; i < configLocal.MaxOpenFiles; i++ {
		wgReadFiles.Add(1)
		go readFile(fileNamesCh, analyzeLineCh, &wgReadFiles)
	}

	var p filePaths
	for _, p.filePath = range filePathList {
		dir, fileName := path.Split(p.filePath)
		// Continue if file have already parsed (has dot in prefix)
		if strings.HasPrefix(fileName, ".") {
			continue
		}
		p.newFilePath = fmt.Sprintf("%v.%v", dir, fileName)

		fileNamesCh <- p
	}
	close(fileNamesCh)
	wgReadFiles.Wait()
	log.Println("All files are parsed")
	close(analyzeLineCh)
	wgAnalyzeLine.Wait()
	log.Println("All lines are analyzed.")
	wgConnMemc.Wait()
	log.Println("All files processed. Exit.")

}
