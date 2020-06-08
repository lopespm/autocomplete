import java.io.IOException;
import java.util.StringTokenizer;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

import org.apache.avro.Schema;
import org.apache.avro.mapred.AvroKey;
import org.apache.avro.mapred.AvroValue;
import org.apache.avro.mapreduce.AvroJob;
import org.apache.avro.mapreduce.AvroKeyInputFormat;
import org.apache.avro.mapreduce.AvroKeyValueOutputFormat;

import org.apache.hadoop.mapreduce.lib.output.MultipleOutputs;
import org.apache.avro.mapreduce.AvroMultipleOutputs;
import org.apache.hadoop.mapreduce.lib.output.LazyOutputFormat;

import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.apache.hadoop.util.GenericOptionsParser;


public class PhrasesWithWeight extends Configured implements Tool{

  private static final String BASE_WEIGHT_KEY = "baseweight";

  public static class PhraseMapper extends Mapper<AvroKey<io.github.lopespm.autocomplete.phrases.value>, NullWritable, Text, LongWritable>{
    private LongWritable baseWeight;

    @Override
    public void setup(Context context) throws IOException, InterruptedException {
      baseWeight = new LongWritable(context.getConfiguration().getInt(BASE_WEIGHT_KEY, 1));
    }

    public void map(AvroKey<io.github.lopespm.autocomplete.phrases.value> key, NullWritable value, Context context) throws IOException, InterruptedException {
      context.write(new Text(key.datum().getPhrase().toString()), baseWeight);
    }
  }

  public static class WeightSumCombiner extends Reducer<Text, LongWritable, Text, LongWritable> {
    private LongWritable weightSumOutput = new LongWritable();
    public void reduce(Text phrase, Iterable<LongWritable> weights, Context context) throws IOException, InterruptedException {
      long weightSum = 0;
      for (LongWritable weight : weights) {
        weightSum += weight.get();
      }
      weightSumOutput.set(weightSum);
      context.write(phrase, weightSumOutput);
    }
  }

  public static class WeightSumReducer extends Reducer<Text, LongWritable, AvroKey<CharSequence>, AvroValue<Long>> {
    public void reduce(Text phrase, Iterable<LongWritable> weights, Context context) throws IOException, InterruptedException {
      long weightSum = 0L;
      for (LongWritable weight : weights) {
        weightSum += weight.get();
      }
      context.write(new AvroKey<CharSequence>(phrase.toString()), new AvroValue<Long>(weightSum));
    }
  }


  public static void main(String[] args) throws Exception {
    int result = ToolRunner.run(new Configuration(), new PhrasesWithWeight(), args);
    System.exit(result);
  }

  @Override
  public int run(String[] args) throws Exception {

    if (args.length != 3) {
      System.err.printf("Usage: %s [generic options] <input> <output> <baseWeight>\n", getClass().getName());
      ToolRunner.printGenericCommandUsage(System.err);
      System.exit(2);
    }

    Path inPath = new Path(args[0]);
    Path outPath = new Path(args[1]);
    Integer baseWeight = Integer.valueOf(args[2]);
    
    Job job = Job.getInstance(getConf(), "Phrases With Weight");
    job.setJarByClass(PhrasesWithWeight.class);

    job.getConfiguration().set("avro.mo.config.namedOutput", inPath.getName());
    job.getConfiguration().setInt(BASE_WEIGHT_KEY, baseWeight);

    job.setMapOutputKeyClass(Text.class);
    job.setMapOutputValueClass(LongWritable.class);

    job.setMapperClass(PhraseMapper.class);
    job.setCombinerClass(WeightSumCombiner.class);
    job.setReducerClass(WeightSumReducer.class);

    AvroJob.setInputKeySchema(job, io.github.lopespm.autocomplete.phrases.value.getClassSchema());
    AvroJob.setOutputKeySchema(job, Schema.create(Schema.Type.STRING));
    AvroJob.setOutputValueSchema(job, Schema.create(Schema.Type.LONG));

    job.setInputFormatClass(AvroKeyInputFormat.class);
    job.setOutputFormatClass(AvroKeyValueOutputFormat.class);

    FileInputFormat.setInputPaths(job, inPath);
    FileOutputFormat.setOutputPath(job, outPath);

    return job.waitForCompletion(true) ? 0 : 1;
  }
}